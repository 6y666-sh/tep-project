"""
src/data_pipeline/preprocess.py의 make_windows() 단위 테스트.

DB/API와 무관한 순수 함수라 합성(synthetic) 데이터로 빠르게 테스트한다.
가장 중요하게 검증하는 것: "결함 런(faultNumber!=0)이어도 warmup_sample
이전 구간은 정상으로 라벨링돼야 한다" — 이 로직이 깨지면 학습 데이터 자체가
오염되고(정상 구간을 이상으로 잘못 학습), 실제로 이 프로젝트 초반에 이 개념을
빼먹었다가 recall이 크게 떨어졌던 이력이 있다.
"""

import numpy as np
import pandas as pd

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_pipeline.preprocess import XMEAS_XMV_COLS, make_windows  # noqa: E402


def _make_synthetic_df(fault_number, run_id, n_samples):
    """faultNumber/simulationRun 하나짜리, 52개 변수 다 채운 합성 데이터프레임."""
    data = {"faultNumber": fault_number, "simulationRun": run_id, "sample": np.arange(1, n_samples + 1)}
    for col in XMEAS_XMV_COLS:
        data[col] = np.arange(n_samples, dtype=float)  # 값 자체는 중요하지 않음, 형태만 맞추면 됨
    return pd.DataFrame(data)


def test_window_count_and_shape():
    df = _make_synthetic_df(fault_number=5, run_id=1, n_samples=30)
    X, y, fault = make_windows(df, window_size=5, stride=5, warmup_sample=10)

    expected_windows = (30 - 5) // 5 + 1  # 6
    assert X.shape == (expected_windows, len(XMEAS_XMV_COLS) * 4)  # mean/std/min/max
    assert y.shape == (expected_windows,)
    assert fault.shape == (expected_windows,)


def test_warmup_before_fault_start_is_labeled_normal():
    """
    윈도우 크기 5, stride 5, warmup 10 기준: 마지막 시점이 sample 5인 첫 윈도우는
    아직 결함 발생 전(warmup 이전)이라 y=0이어야 하고, sample 20짜리 윈도우는
    결함 발생 후라 y=1이어야 한다.
    """
    df = _make_synthetic_df(fault_number=7, run_id=1, n_samples=30)
    X, y, fault = make_windows(df, window_size=5, stride=5, warmup_sample=10)

    # 윈도우 순서대로 마지막 시점 sample: 5, 10, 15, 20, 25, 30
    assert y[0] == 0   # 마지막 시점 sample=5 < warmup(10) -> 정상
    assert y[1] == 1   # 마지막 시점 sample=10 >= warmup(10) -> 이상
    assert y[-1] == 1  # sample=30 -> 이상
    # fault_number 자체은 라벨과 무관하게 항상 그 런의 faultNumber로 채워진다
    assert (fault == 7).all()


def test_fault_number_zero_always_normal_regardless_of_sample():
    """faultNumber=0(정상 런)은 warmup 여부와 상관없이 전부 y=0이어야 한다."""
    df = _make_synthetic_df(fault_number=0, run_id=1, n_samples=30)
    X, y, fault = make_windows(df, window_size=5, stride=5, warmup_sample=10)

    assert (y == 0).all()
    assert (fault == 0).all()


def test_multiple_runs_grouped_independently():
    """
    서로 다른 (faultNumber, simulationRun) 조합은 독립적으로 슬라이딩 윈도우를
    만들어야 한다 — 런 경계를 넘어 섞이면(예: run1의 끝과 run2의 시작을 이어붙여
    윈도우를 만들면) 물리적으로 말이 안 되는 가짜 시계열이 생긴다.
    """
    df1 = _make_synthetic_df(fault_number=0, run_id=1, n_samples=10)
    df2 = _make_synthetic_df(fault_number=0, run_id=2, n_samples=10)
    df = pd.concat([df1, df2], ignore_index=True)

    X, y, fault = make_windows(df, window_size=5, stride=5, warmup_sample=10)

    # 런 하나당 (10-5)//5+1 = 2개 윈도우, 런이 둘이니 총 4개
    assert X.shape[0] == 4
