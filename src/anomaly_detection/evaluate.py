"""
베이스라인 이상탐지 모델 평가

- train_baseline.py에서 저장한 모델 + threshold를 불러와 test 데이터에 적용
- 정확도 하나만 보지 않는 이유: 이상 비율이 56%로 이미 한쪽에 치우쳐 있어서
  (train 문서 참고) accuracy만으로는 "그냥 다 이상이라고 찍어도 56% 맞는" 함정에 빠질
  수 있다. 그래서 precision/recall/F1/ROC-AUC를 같이 본다.
- confidence: 하네스(orchestration) 단계에서 "판정 신뢰도가 낮으면 재분석 절차로
  전환"하는 로직에 쓸 값. anomaly score를 0~1 범위로 정규화해서 만든다.
"""

import json

import joblib
import numpy as np
from sklearn.metrics import (
    confusion_matrix,
    precision_recall_fscore_support,
    roc_auc_score,
)

DATA_PATH = "data/processed/windows.npz"
MODEL_PATH = "models/isolation_forest_baseline.joblib"
META_PATH = "models/isolation_forest_meta.json"


def scores_to_confidence(scores, threshold, train_scores):
    """
    decision_function 점수를 0~1 사이의 "이상 확신도(confidence)"로 변환.

    설계 방식: threshold보다 점수가 낮을수록(더 이상에 가까울수록) confidence를 높게,
    threshold보다 높을수록(정상에 가까울수록) confidence를 낮게(=정상이라는 확신) 준다.
    정상 학습 데이터 점수의 최솟값을 하한선으로 잡아 0~1로 clip한다.

    주의: 이건 통계적으로 엄밀한 확률이 아니라 "점수를 threshold 기준 상대적
    거리로 정규화한 휴리스틱"이다. 나중에 하네스 로직에서 "confidence가 낮으면
    재분석"이라는 판단에 쓸 상대적 지표로만 활용한다.
    """
    lower_bound = train_scores.min()
    span = max(threshold - lower_bound, 1e-9)
    confidence = (threshold - scores) / span
    return np.clip(confidence, 0.0, 1.0)


def main():
    data = np.load(DATA_PATH)
    X_test, y_test, fault_test = data["X_test"], data["y_test"], data["fault_test"]
    X_train, y_train = data["X_train"], data["y_train"]

    model = joblib.load(MODEL_PATH)
    with open(META_PATH, encoding="utf-8") as f:
        meta = json.load(f)
    threshold = meta["threshold"]

    train_scores = model.decision_function(X_train[y_train == 0])
    test_scores = model.decision_function(X_test)

    # score < threshold 이면 이상(1), 아니면 정상(0)
    y_pred = (test_scores < threshold).astype(int)
    confidence = scores_to_confidence(test_scores, threshold, train_scores)

    # ===== 전체 성능 =====
    tn, fp, fn, tp = confusion_matrix(y_test, y_pred).ravel()
    precision, recall, f1, _ = precision_recall_fscore_support(
        y_test, y_pred, average="binary", zero_division=0
    )
    # roc_auc는 예측 라벨이 아니라 연속 점수로 계산 (점수가 낮을수록 이상이므로 부호 반전)
    roc_auc = roc_auc_score(y_test, -test_scores)

    print("=" * 50)
    print("전체 성능")
    print("=" * 50)
    print(f"Confusion Matrix: TN={tn}  FP={fp}  FN={fn}  TP={tp}")
    print(f"Precision: {precision:.3f}")
    print(f"Recall:    {recall:.3f}")
    print(f"F1-score:  {f1:.3f}")
    print(f"ROC-AUC:   {roc_auc:.3f}")
    print(f"평균 confidence(이상 판정 건): {confidence[y_pred == 1].mean():.3f}")

    # ===== 결함 유형별 탐지율 =====
    # 목적: 어떤 결함은 잘 잡고 어떤 결함은 잘 못 잡는지 확인 (면접/보고서에 활용)
    print()
    print("=" * 50)
    print("결함 유형별 탐지율 (재현율, 해당 결함의 이상 구간만 대상)")
    print("=" * 50)
    for fault_no in sorted(set(fault_test) - {0}):
        mask = (fault_test == fault_no) & (y_test == 1)
        if mask.sum() == 0:
            continue
        fault_recall = y_pred[mask].mean()
        print(f"Fault {int(fault_no):>2}: 탐지율 {fault_recall:.1%}  (평가 윈도우 {mask.sum()}개)")


if __name__ == "__main__":
    main()
