import pandas as pd
import numpy as np
from sklearn.preprocessing import StandardScaler

XMEAS_XMV_COLS = [c for c in [f"xmeas_{i}" for i in range(1, 42)] + [f"xmv_{i}" for i in range(1, 12)]]

def make_windows(df, window_size=10, stride=5, warmup_sample=20):
    """
    simulationRun(+faultNumber) 단위로 그룹핑 후 슬라이딩 윈도우 생성.
    - 요약통계(mean/std/min/max) 방식으로 윈도우를 벡터화 (Isolation Forest 입력용)
    - 라벨은 윈도우 마지막 시점 기준

    왜 warmup_sample이 필요한가:
    TEP 데이터셋은 faultNumber!=0인 런이라도 처음 몇 개 샘플은 아직 결함이
    발생하기 전(정상 거동)이다. Rieth et al. 데이터셋 관례상 학습용 런은
    20번째 샘플부터, 테스트용 런은 160번째 샘플부터 실제 결함이 시작된다.
    이걸 무시하고 "결함 런에 속하면 무조건 이상"으로 라벨링하면, 실제로는
    정상인 구간까지 이상으로 잘못 라벨링해 학습 데이터가 오염된다.
    """
    feature_rows = []
    labels = []
    fault_numbers = []

    for (fault_no, run_id), g in df.groupby(["faultNumber", "simulationRun"]):
        g = g.sort_values("sample").reset_index(drop=True)
        values = g[XMEAS_XMV_COLS].values

        for start in range(0, len(g) - window_size + 1, stride):
            window = values[start:start + window_size]
            feat = np.concatenate([
                window.mean(axis=0),
                window.std(axis=0),
                window.min(axis=0),
                window.max(axis=0),
            ])
            feature_rows.append(feat)

            last_row = g.loc[start + window_size - 1]
            # 결함 런이어도(faultNumber!=0) 워밍업 구간 이전(sample<warmup_sample)이면
            # 아직 결함이 발생하지 않은 정상 구간으로 판단
            is_anomaly = bool(last_row["faultNumber"] != 0 and last_row["sample"] >= warmup_sample)
            labels.append(int(is_anomaly))
            fault_numbers.append(fault_no)

    return np.array(feature_rows), np.array(labels), np.array(fault_numbers)


if __name__ == "__main__":
    train_normal = pd.read_parquet("data/processed/fault_free_training.parquet")
    train_faulty = pd.read_parquet("data/processed/faulty_training.parquet")
    test_normal = pd.read_parquet("data/processed/fault_free_testing.parquet")
    test_faulty = pd.read_parquet("data/processed/faulty_testing.parquet")

    # 프로토타입 단계라 런 개수 줄여서 시작 (나중에 늘리기)
    train_faulty = train_faulty[train_faulty["simulationRun"] <= 50]
    test_faulty = test_faulty[test_faulty["simulationRun"] <= 50]

    train_df = pd.concat([train_normal, train_faulty], ignore_index=True)
    test_df = pd.concat([test_normal, test_faulty], ignore_index=True)

    # training 파일은 20번째 샘플, testing 파일은 160번째 샘플부터 결함 시작
    # (Rieth et al. TEP 데이터셋 관례)
    X_train_raw, y_train, fault_train = make_windows(train_df, warmup_sample=20)
    X_test_raw, y_test, fault_test = make_windows(test_df, warmup_sample=160)

    # 정상 데이터(y_train==0)에만 fit: 비지도 이상탐지는 "정상 패턴만 학습"하는
    # 것이 기본 가정이고, test 통계가 학습에 섞이면 데이터 누수가 되기 때문
    scaler = StandardScaler()
    scaler.fit(X_train_raw[y_train == 0])

    X_train = scaler.transform(X_train_raw)
    X_test = scaler.transform(X_test_raw)

    print("train:", X_train.shape, "test:", X_test.shape)
    print("train 이상 비율:", y_train.mean(), "test 이상 비율:", y_test.mean())

    np.savez("data/processed/windows.npz",
             X_train=X_train, y_train=y_train,
             X_test=X_test, y_test=y_test,
             fault_train=fault_train, fault_test=fault_test)