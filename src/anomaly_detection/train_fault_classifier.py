"""
결함 유형 분류기 학습 (RandomForest, 다중분류)

왜 필요한가:
Isolation Forest(베이스라인)는 "정상이냐 이상이냐"만 판단하고, 20가지 결함 중
어떤 결함인지는 구분하지 못한다. 기획서 출력 스펙(`fault_number`)을 채우려면
"이상으로 판정된 경우, 어떤 결함일 가능성이 높은지"를 추가로 분류해야 한다.

왜 RandomForest인가:
- 지도학습 다중분류 문제라(정답 fault_number가 이미 데이터에 있음), 비지도
  방식인 Isolation Forest와는 다른 문제. 라벨이 있으니 지도학습을 쓰는 게 자연스러움
- 트리 앙상블이라 학습이 빠르고, 클래스 간 스케일 차이에 민감하지 않으며,
  파인튜닝 없는 전통 ML 제약에도 맞음 (LSTM 등 딥러닝 없이도 합리적 baseline)

왜 정상(fault_number=0) 데이터는 빼고 학습하는가:
이 분류기의 역할은 "이미 이상으로 판정된 것 중에서 어떤 결함인지" 맞히는 것이라,
정상 데이터까지 넣으면 문제 정의가 달라진다(그건 Isolation Forest의 역할).
그래서 y_train==1(이상)인 윈도우만 골라서 fault_number를 라벨로 학습시킨다.
"""

import json
import os

import joblib
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report

DATA_PATH = "data/processed/windows.npz"
MODEL_DIR = "models"
MODEL_PATH = os.path.join(MODEL_DIR, "fault_classifier.joblib")
META_PATH = os.path.join(MODEL_DIR, "fault_classifier_meta.json")


def main():
    data = np.load(DATA_PATH)
    X_train, y_train, fault_train = data["X_train"], data["y_train"], data["fault_train"]
    X_test, y_test, fault_test = data["X_test"], data["y_test"], data["fault_test"]

    # 이상으로 라벨링된 윈도우만 사용 (정상은 애초에 fault_number=0이라 분류 대상이 아님)
    train_mask = y_train == 1
    test_mask = y_test == 1
    X_train_f, y_fault_train = X_train[train_mask], fault_train[train_mask]
    X_test_f, y_fault_test = X_test[test_mask], fault_test[test_mask]

    print(f"결함 분류 학습 데이터: {X_train_f.shape[0]}개, 결함 종류: {len(set(y_fault_train))}가지")

    # n_estimators=200: 이상탐지 모델과 동일 기준 (속도/성능 균형)
    # class_weight='balanced': 결함 유형별로 데이터 양이 다를 수 있어서, 적은 유형이
    # 무시되지 않도록 클래스 비율에 반비례해서 가중치를 줌
    clf = RandomForestClassifier(
        n_estimators=200,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    clf.fit(X_train_f, y_fault_train)

    y_pred = clf.predict(X_test_f)
    acc = accuracy_score(y_fault_test, y_pred)
    print(f"\n결함 유형 분류 정확도: {acc:.3f}")
    print(classification_report(y_fault_test, y_pred, zero_division=0))

    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(clf, MODEL_PATH)

    meta = {"accuracy": float(acc), "n_estimators": 200, "classes": sorted(set(int(f) for f in y_fault_train))}
    with open(META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)

    print(f"\n모델 저장 완료: {MODEL_PATH}")


if __name__ == "__main__":
    main()
