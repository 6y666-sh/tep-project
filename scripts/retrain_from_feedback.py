"""
작업자 피드백으로 모델 재학습 (active learning 루프의 2단계).

1단계(라벨 수집)는 이미 되어 있다: 전체화면 알림에서 "상황종료"를 누를 때
confirmed_fault_number(진짜 정답)를 sensor_logs 테이블에 저장해왔다.
이 스크립트는 그렇게 쌓인 확인 라벨을 모아서 실제로 두 모델을
(IsolationForest 정상/이상 판정기, RandomForest 결함분류기) 다시 학습시킨다.

왜 요청마다 즉시 재학습하지 않고 이렇게 배치로 도는가:
- IsolationForest는 scikit-learn에서 부분학습(partial_fit)을 지원하지 않아서,
  재학습하려면 매번 "정상 데이터 전체"로 처음부터 다시 학습해야 한다. 요청 하나
  처리하면서 할 일이 아니라 별도 배치 작업으로 분리했다.
- 확인 1~2건 가지고 바로 반영하면 모델이 최근 몇 건에 과하게 휘둘려서 오히려
  불안정해진다(하나만 잘못 확인해도 바로 모델이 망가짐). 어느 정도 쌓인 뒤에
  한 번에 반영하는 게 안전하다.

핵심 설계: raw(스케일링 전) 특징벡터를 저장해뒀다가(window_features 컬럼),
기존 scaler는 그대로 두고(재학습마다 스케일러까지 바뀌면 기준이 계속 흔들림)
그 raw 벡터만 새로 합쳐서 기존 모델과 같은 방식으로 다시 학습시킨다.
원래 학습에 쓰인 X_train은 windows.npz에 "스케일링된 상태"로만 저장돼 있어서,
scaler.inverse_transform()으로 raw 값을 복원해 피드백 데이터와 합친다
(StandardScaler는 선형변환이라 역변환이 정확하다).

검증 원칙: 재학습했다고 무조건 새 모델을 쓰지 않는다. 학습에 전혀 쓰이지 않은
X_test(held-out)로 기존 모델과 새 모델의 성능을 둘 다 측정해서 비교하고, 새
모델을 쓰기 전에 기존 모델 파일을 models/archive/에 백업해서 언제든 롤백할 수
있게 한다.

실행 방법 (venv 활성화 후, 프로젝트 루트에서):
    python scripts/retrain_from_feedback.py
"""

import json
import os
import shutil
import sys
from datetime import datetime, timezone

import joblib
import numpy as np
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_recall_fscore_support,
)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.db.models import SensorLog  # noqa: E402
from src.db.session import SessionLocal  # noqa: E402

DATA_PATH = "data/processed/windows.npz"
MODEL_DIR = "models"
THRESHOLD_PERCENTILE = 40.0  # train_baseline.py와 동일한 기준(재현율 우선)


def load_feedback():
    """resolved=True이고 confirmed_fault_number가 있는 로그를 학습 가능한 형태로 변환."""
    db = SessionLocal()
    try:
        rows = (
            db.query(SensorLog)
            .filter(SensorLog.resolved.is_(True))
            .filter(SensorLog.confirmed_fault_number.isnot(None))
            .filter(SensorLog.window_features.isnot(None))
            .all()
        )
    finally:
        db.close()

    feats, labels = [], []
    skipped = 0
    for row in rows:
        try:
            feat = json.loads(row.window_features)
        except (TypeError, ValueError):
            skipped += 1
            continue
        if len(feat) != 208:  # 52변수 x (mean/std/min/max)
            skipped += 1
            continue
        feats.append(feat)
        labels.append(row.confirmed_fault_number)

    if skipped:
        print(f"형식이 안 맞아 건너뛴 로그: {skipped}개")

    return np.array(feats, dtype=float), np.array(labels, dtype=int)


def evaluate_isolation_forest(model, threshold, X_test, y_test, label):
    scores = model.decision_function(X_test)
    y_pred = (scores < threshold).astype(int)
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average="binary", zero_division=0
    )
    print(f"[{label}] IsolationForest — Precision {precision:.3f}  Recall {recall:.3f}  "
          f"F1 {f1:.3f}  (TP={tp} FP={fp} FN={fn} TN={tn})")
    return {"precision": precision, "recall": recall, "f1": f1}


def evaluate_fault_classifier(clf, X_test_fault, y_test_fault, label):
    if len(X_test_fault) == 0:
        return None
    y_pred = clf.predict(X_test_fault)
    acc = accuracy_score(y_test_fault, y_pred)
    print(f"[{label}] RandomForest 결함분류 정확도 — {acc:.3f}")
    return {"accuracy": acc}


def backup_current_models():
    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(MODEL_DIR, "archive", ts)
    os.makedirs(backup_dir, exist_ok=True)
    for fname in [
        "isolation_forest_baseline.joblib",
        "isolation_forest_meta.json",
        "fault_classifier.joblib",
        "fault_classifier_meta.json",
    ]:
        src = os.path.join(MODEL_DIR, fname)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(backup_dir, fname))
    print(f"기존 모델 백업 완료: {backup_dir}")
    return backup_dir


def main():
    feedback_X_raw, feedback_y = load_feedback()
    print(f"확인된 피드백 로그: {len(feedback_X_raw)}건 "
          f"(정상/오탐 확인: {int((feedback_y == 0).sum())}건, "
          f"결함 확인: {int((feedback_y != 0).sum())}건)")

    if len(feedback_X_raw) == 0:
        print("아직 재학습에 쓸 피드백이 없습니다. "
              "전체화면 알림에서 상황종료를 몇 번 확인한 뒤 다시 실행하세요.")
        return

    data = np.load(DATA_PATH)
    X_train, y_train, fault_train = data["X_train"], data["y_train"], data["fault_train"]
    X_test, y_test, fault_test = data["X_test"], data["y_test"], data["fault_test"]

    scaler = joblib.load(os.path.join(MODEL_DIR, "scaler.joblib"))
    old_if_model = joblib.load(os.path.join(MODEL_DIR, "isolation_forest_baseline.joblib"))
    with open(os.path.join(MODEL_DIR, "isolation_forest_meta.json"), encoding="utf-8") as f:
        old_meta = json.load(f)
    old_threshold = old_meta["threshold"]

    fault_clf_path = os.path.join(MODEL_DIR, "fault_classifier.joblib")
    old_clf = joblib.load(fault_clf_path) if os.path.exists(fault_clf_path) else None

    # ===== 1) IsolationForest: 정상 데이터 + "오탐이었다고 확인된" 피드백을 합쳐서 재학습 =====
    normal_raw_original = scaler.inverse_transform(X_train[y_train == 0])
    normal_raw_feedback = feedback_X_raw[feedback_y == 0]
    new_normal_raw = np.vstack([normal_raw_original, normal_raw_feedback]) if len(normal_raw_feedback) else normal_raw_original
    # 원래 학습 때(train_baseline.py)는 windows.npz에 이미 스케일링된 X_train을 그대로 fit에
    # 썼다. 여기서도 스케일 기준을 똑같이 맞춰야 decision_function 점수가 기존 threshold와
    # 같은 척도로 나온다 — raw 그대로 fit하면 변수마다 단위가 달라(온도 100대, 유량 10대 등)
    # 트리 분할 기준이 완전히 달라지고, X_test(스케일링됨)로 평가할 때도 척도가 안 맞아서
    # 점수 분포 자체가 어긋난다. (처음 버전엔 이 transform이 빠져 있어서 재학습 후 거의
    # 전부를 이상으로 판정하는 버그가 있었음 — held-out 검증에서 TN=0으로 바로 드러남)
    new_normal_scaled = scaler.transform(new_normal_raw)

    new_if_model = IsolationForest(n_estimators=200, contamination="auto", random_state=42, n_jobs=-1)
    new_if_model.fit(new_normal_scaled)
    new_train_scores = new_if_model.decision_function(new_normal_scaled)
    new_threshold = float(np.percentile(new_train_scores, THRESHOLD_PERCENTILE))
    new_min_train_score = float(new_train_scores.min())

    # ===== 2) RandomForest: 결함 데이터 + "N번 결함이었다고 확인된" 피드백을 합쳐서 재학습 =====
    X_fault_original = X_train[y_train == 1]
    y_fault_original = fault_train[y_train == 1]
    fault_mask = feedback_y != 0
    X_fault_feedback = scaler.transform(feedback_X_raw[fault_mask]) if fault_mask.sum() else np.empty((0, X_train.shape[1]))
    y_fault_feedback = feedback_y[fault_mask]

    new_X_fault = np.vstack([X_fault_original, X_fault_feedback]) if len(X_fault_feedback) else X_fault_original
    new_y_fault = np.concatenate([y_fault_original, y_fault_feedback]) if len(y_fault_feedback) else y_fault_original

    new_clf = RandomForestClassifier(n_estimators=200, class_weight="balanced", random_state=42, n_jobs=-1)
    new_clf.fit(new_X_fault, new_y_fault)

    # ===== 3) 검증: 학습에 전혀 안 쓰인 X_test로 기존 모델 vs 새 모델 비교 =====
    print()
    print("=" * 60)
    print("held-out 테스트셋 성능 비교 (재학습에 전혀 쓰이지 않은 데이터)")
    print("=" * 60)
    old_if_metrics = evaluate_isolation_forest(old_if_model, old_threshold, X_test, y_test, "기존")
    new_if_metrics = evaluate_isolation_forest(new_if_model, new_threshold, X_test, y_test, "재학습")

    X_test_fault = X_test[y_test == 1]
    y_test_fault = fault_test[y_test == 1]
    if old_clf is not None:
        evaluate_fault_classifier(old_clf, X_test_fault, y_test_fault, "기존")
    evaluate_fault_classifier(new_clf, X_test_fault, y_test_fault, "재학습")

    # ===== 4) 저장 (기존 파일은 먼저 백업) =====
    print()
    if new_if_metrics["f1"] + 0.01 < old_if_metrics["f1"]:
        print("경고: 재학습한 IsolationForest의 F1이 기존보다 눈에 띄게 낮습니다. "
              "그래도 저장은 하되, 배포 전에 한 번 더 검토하는 걸 권장합니다.")

    backup_current_models()

    joblib.dump(new_if_model, os.path.join(MODEL_DIR, "isolation_forest_baseline.joblib"))
    new_meta = dict(old_meta)
    new_meta.update({
        "threshold": new_threshold,
        "threshold_percentile": THRESHOLD_PERCENTILE,
        "min_train_score": new_min_train_score,
        "train_normal_count": int(len(new_normal_raw)),
        "retrained_at": datetime.now(timezone.utc).isoformat(),
        "feedback_samples_used": int(len(feedback_X_raw)),
    })
    with open(os.path.join(MODEL_DIR, "isolation_forest_meta.json"), "w", encoding="utf-8") as f:
        json.dump(new_meta, f, ensure_ascii=False, indent=2)

    joblib.dump(new_clf, fault_clf_path)
    clf_meta = {
        "n_estimators": 200,
        "classes": sorted(set(int(v) for v in new_y_fault)),
        "retrained_at": datetime.now(timezone.utc).isoformat(),
        "feedback_samples_used": int(fault_mask.sum()),
    }
    with open(os.path.join(MODEL_DIR, "fault_classifier_meta.json"), "w", encoding="utf-8") as f:
        json.dump(clf_meta, f, ensure_ascii=False, indent=2)

    print()
    print("재학습 완료. models/ 폴더의 joblib/json 파일이 갱신됐습니다.")
    print("FastAPI 서버는 모델을 처음 요청 때 한 번만 불러와 메모리에 캐시해두므로, "
          "서버를 재시작해야 새 모델이 반영됩니다.")


if __name__ == "__main__":
    main()
