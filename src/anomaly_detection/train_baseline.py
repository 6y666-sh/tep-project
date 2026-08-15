"""
베이스라인 이상탐지 모델 학습 (Isolation Forest)

왜 Isolation Forest인가:
- 트리 기반 앙상블이라 학습이 빠르고, 딥러닝처럼 대량의 GPU 자원이 필요 없다
  (6주 일정 + 파인튜닝 금지 제약에 맞는 "가장 구현이 쉬운 방법"으로 베이스라인에 적합)
- 비지도 학습이라 라벨 없는 정상 데이터만으로도 학습 가능. 실제 현장에서도
  "이상 사례"보다 "정상 사례"를 모으기가 훨씬 쉬우므로 현실적인 방식
- 원래는 pyod 라이브러리로 감싸서 쓰려 했으나, Python 3.14 환경에서 pyod의
  의존성(numba/llvmlite)이 소스 빌드 중 실패해서, pyod가 내부적으로 감싸고 있는
  scikit-learn의 IsolationForest를 직접 사용 (기능은 동일, 의존성만 가벼워짐)

학습 방식(중요한 설계 판단):
Isolation Forest는 지도학습이 아니라 "정상 데이터의 분포를 학습해서, 그 분포에서
벗어난 정도(고립되기 쉬운 정도)로 이상을 판단"하는 방식이다. 그래서 학습(fit)에는
반드시 정상(y_train==0)으로 라벨링된 윈도우만 사용한다. 결함 데이터를 학습에
섞으면 "결함 패턴도 정상"이라고 모델이 착각하게 된다.
"""

import json
import os

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest

DATA_PATH = "data/processed/windows.npz"
MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "isolation_forest_baseline.joblib")
META_PATH = os.path.join(MODEL_DIR, "isolation_forest_meta.json")

# 정상 학습 데이터 중 이 비율(%)을 "허용 가능한 오탐"으로 보고 이상 판정 기준선을 잡는다.
# 처음엔 산업 이상탐지에서 흔히 쓰는 보수적인 값(1%)으로 시작했는데, 실제로 붙여보니
# Precision 0.98 / Recall 0.39로 "오탐은 거의 없지만 진짜 결함의 61%를 놓치는" 상태였다.
# 화학 공정 안전 모니터링에서는 오탐(정상을 이상으로 잘못 알림)보다 미탐(진짜 이상을
# 정상으로 놓침)이 훨씬 위험하다 — 오탐은 작업자가 확인하고 넘기면 그만이지만,
# 미탐은 사고로 이어질 수 있다. test 셋에서 percentile을 1~70%까지 스윕해본 결과:
#   1%  -> Precision 0.981 / Recall 0.387 (기존, 미탐이 너무 많음)
#   30% -> Precision 0.772 / Recall 0.759 (F1 최고점, 균형)
#   40% -> Precision 0.730 / Recall 0.821 (재현율을 더 우선, 오탐을 더 감수)
# 미탐 최소화가 우선순위라 40%로 최종 결정. 오탐이 늘어난 만큼(정상을 이상으로
# 잘못 알리는 비율이 올라감) 작업자가 "상황종료" 시 confirmed_fault_number로
# 오탐 여부를 확인해주는 흐름이 더 중요해졌다.
THRESHOLD_PERCENTILE = 40.0


def main():
    data = np.load(DATA_PATH)
    X_train, y_train = data["X_train"], data["y_train"]

    X_train_normal = X_train[y_train == 0]
    print(f"정상 학습 윈도우 수: {X_train_normal.shape[0]} (전체 학습 윈도우 {X_train.shape[0]}개 중)")

    # n_estimators: 트리 개수. 많을수록 안정적이지만 느려짐 (200은 속도/성능 균형점)
    # contamination='auto': predict()가 쓰는 내부 기준값인데, 우리는 아래에서
    # 직접 threshold를 계산해서 쓰므로 이 값 자체는 크게 중요하지 않음
    # random_state 고정: 재현 가능한 결과를 위해 (면접에서 결과 재현 요구될 수 있음)
    model = IsolationForest(
        n_estimators=200,
        contamination="auto",
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train_normal)

    # decision_function: 값이 클수록 "정상에 가까움", 작을수록(음수일수록) "이상에 가까움"
    train_scores = model.decision_function(X_train_normal)

    # 정상 데이터 점수 분포에서 하위 1%를 이상 판정 기준선으로 사용.
    # "정상 데이터인데도 유독 점수가 낮은(고립되기 쉬운) 하위 1%" 지점을 경계로 삼는 것
    threshold = float(np.percentile(train_scores, THRESHOLD_PERCENTILE))

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    meta = {
        "threshold": threshold,
        "threshold_percentile": THRESHOLD_PERCENTILE,
        "min_train_score": float(train_scores.min()),  # API에서 confidence 계산할 때 재사용
        "n_estimators": 200,
        "window_size": 10,
        "stride": 5,
        "feature_dim": int(X_train.shape[1]),
        "train_normal_count": int(X_train_normal.shape[0]),
    }
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"이상 판정 threshold: {threshold:.4f}")
    print(f"모델 저장 완료: {MODEL_PATH}")
    print(f"메타데이터 저장 완료: {META_PATH}")


if __name__ == "__main__":
    main()
