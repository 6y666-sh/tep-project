"""
POST /anomaly-check

센서 데이터 윈도우를 받아 이상탐지 결과를 반환한다.
train_baseline.py(정상/이상 판정) + train_fault_classifier.py(결함 유형 추정)
두 모델을 순서대로 태운다: 먼저 이상 여부를 판단하고, 이상일 때만 결함 유형을 분류한다
(fault_classifier 자체가 "이상으로 판정된 것 중 어떤 결함이냐"만 학습했으므로).
"""

import json
import os

import joblib
import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from src.api.schemas import AnomalyCheckRequest, AnomalyCheckResponse
from src.db.models import SensorLog
from src.db.session import get_db

router = APIRouter()

MODEL_DIR = "models"
EXPECTED_VARS = 52  # xmeas_1..41 + xmv_1..11

# 모듈 전역에 한 번만 로드해두고 재사용 (요청마다 joblib.load 하면 느림)
_state = {"loaded": False}


def _load_artifacts():
    if _state["loaded"]:
        return

    model_path = os.path.join(MODEL_DIR, "isolation_forest_baseline.joblib")
    scaler_path = os.path.join(MODEL_DIR, "scaler.joblib")
    meta_path = os.path.join(MODEL_DIR, "isolation_forest_meta.json")
    fault_clf_path = os.path.join(MODEL_DIR, "fault_classifier.joblib")

    if not (os.path.exists(model_path) and os.path.exists(scaler_path) and os.path.exists(meta_path)):
        raise RuntimeError(
            "모델 파일이 없습니다. train_baseline.py와 preprocess.py(scaler 저장)를 먼저 실행하세요."
        )

    _state["model"] = joblib.load(model_path)
    _state["scaler"] = joblib.load(scaler_path)
    with open(meta_path, encoding="utf-8") as f:
        _state["meta"] = json.load(f)
    _state["fault_clf"] = joblib.load(fault_clf_path) if os.path.exists(fault_clf_path) else None
    _state["loaded"] = True


def _window_to_features(window: list[list[float]]) -> np.ndarray:
    """윈도우(시점 x 52변수)를 학습 때와 동일한 요약통계(mean/std/min/max) 벡터로 변환."""
    arr = np.array(window, dtype=float)
    feat = np.concatenate([arr.mean(axis=0), arr.std(axis=0), arr.min(axis=0), arr.max(axis=0)])
    return feat.reshape(1, -1)


def _score_to_confidence(score: float, threshold: float, min_train_score: float) -> float:
    """evaluate.py의 scores_to_confidence와 동일한 방식 (threshold 기준 상대 거리를 0~1로 정규화)."""
    span = max(threshold - min_train_score, 1e-9)
    return float(np.clip((threshold - score) / span, 0.0, 1.0))


@router.post("/anomaly-check", response_model=AnomalyCheckResponse)
def anomaly_check(req: AnomalyCheckRequest, db: Session = Depends(get_db)):
    _load_artifacts()

    if not req.window or any(len(row) != EXPECTED_VARS for row in req.window):
        raise HTTPException(
            status_code=400,
            detail=f"window의 각 시점은 {EXPECTED_VARS}개 값(xmeas_1..41, xmv_1..11)이어야 합니다.",
        )

    raw_feat = _window_to_features(req.window)
    scaled_feat = _state["scaler"].transform(raw_feat)

    score = float(_state["model"].decision_function(scaled_feat)[0])
    threshold = _state["meta"]["threshold"]
    is_anomaly = score < threshold
    confidence = _score_to_confidence(score, threshold, _state["meta"]["min_train_score"])

    fault_number = None
    if is_anomaly and _state["fault_clf"] is not None:
        fault_number = int(_state["fault_clf"].predict(scaled_feat)[0])

    # 센서 로그 + 결함 이력 DB 기록 (기획서 3-4: "DB: MySQL (센서 로그, 결함 이력)")
    # window의 마지막 시점(가장 최근 값)만 저장 — 대시보드의 설비별 그래프는
    # "지금 이 순간의 센서 값이 어떻게 변해왔는지"를 보여주려는 목적이라
    # 윈도우 전체(10개 시점)를 다 저장할 필요는 없다.
    db.add(
        SensorLog(
            is_anomaly=is_anomaly,
            fault_number=fault_number,
            confidence=confidence,
            sensor_values=json.dumps(req.window[-1]),
        )
    )
    db.commit()

    return AnomalyCheckResponse(is_anomaly=is_anomaly, fault_number=fault_number, confidence=confidence)
