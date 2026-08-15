"""
실시간 공장 가동 시뮬레이터.

실제 TEP 테스트 시뮬레이션 run 하나를 처음(정상)부터 끝(결함 진행)까지 순서대로
재생하면서, 실제 센서가 데이터를 보내는 것과 똑같이 일정 간격으로 /anomaly-check
API를 호출한다. 프론트엔드는 이미 폴링 중이므로(대시보드 5초, 알림 3초 간격),
이 스크립트만 돌려두면 화면이 "진짜 공장이 돌아가는 것처럼" 계속 갱신된다.
별도의 프론트/백엔드 코드 수정 없이, 실제 배포 시 센서 게이트웨이가 할 일을
그대로 흉내내는 방식이라 가장 사실적이다.

Rieth et al. TEP 테스트 데이터셋 규칙 (preprocess.py의 make_windows와 동일 기준):
- 테스트용 run은 샘플 1~960까지 있고, 결함은 160번째 샘플부터 시작된다.
  즉 faultNumber가 지정된 run이라도 처음 ~160개 샘플은 실제로는 정상 거동이고,
  160번째부터 진짜 이상 신호가 섞이기 시작한다 — "정상 가동 중이다가 중간에
  결함이 발생해서 서서히 드러나는" 실제 공정과 같은 흐름이 재현된다.
- 슬라이딩 윈도우도 학습 때와 같은 방식(size=10, stride=5)으로 만들어서
  실제 배포 시나리오(최근 10개 시점을 모아 판정 요청)와 동일하게 흉내낸다.

사용법 (venv 활성화 후, FastAPI 서버(uvicorn)를 먼저 띄운 상태에서 별도 터미널에):
    python scripts/simulate_plant.py                       # 기본값(결함 4번, run 1)
    python scripts/simulate_plant.py --fault 6 --run 3      # 다른 결함/run 재생
    python scripts/simulate_plant.py --interval 2           # 2초 간격으로 재생 (기본 3초)
    python scripts/simulate_plant.py --host http://localhost:8000
    Ctrl+C로 언제든 중단 가능.
"""

import argparse
import sys
import time

import httpx
import pandas as pd

XMEAS_XMV_COLS = [f"xmeas_{i}" for i in range(1, 42)] + [f"xmv_{i}" for i in range(1, 12)]
WINDOW_SIZE = 10
STRIDE = 5
WARMUP_SAMPLE = 160  # 테스트용 run 기준, 이 샘플부터 실제 결함 시작 (preprocess.py와 동일)


def load_run(fault_number: int, run_id: int) -> pd.DataFrame:
    # filters로 predicate pushdown: 858MB 파일 전체를 안 읽고 해당 run만 골라 읽는다
    df = pd.read_parquet(
        "data/processed/faulty_testing.parquet",
        filters=[("faultNumber", "=", fault_number), ("simulationRun", "=", float(run_id))],
    )
    if df.empty:
        raise SystemExit(f"faultNumber={fault_number}, simulationRun={run_id} 데이터를 찾을 수 없습니다.")
    return df.sort_values("sample").reset_index(drop=True)


def main():
    parser = argparse.ArgumentParser(description="TEP 실시간 공장 가동 시뮬레이터")
    parser.add_argument("--fault", type=int, default=4, help="재생할 결함 번호 (1~20, 기본 4)")
    parser.add_argument("--run", type=int, default=1, help="simulationRun 번호 (기본 1)")
    parser.add_argument("--interval", type=float, default=3.0, help="윈도우 사이 대기 시간(초, 기본 3)")
    parser.add_argument("--stride", type=int, default=STRIDE, help="윈도우 이동 간격(샘플 수, 기본 5)")
    parser.add_argument("--host", type=str, default="http://localhost:8000", help="FastAPI 서버 주소")
    args = parser.parse_args()

    df = load_run(args.fault, args.run)
    values = df[XMEAS_XMV_COLS].values
    samples = df["sample"].values
    total_samples = int(samples[-1])

    n_windows = (len(df) - WINDOW_SIZE) // args.stride + 1
    print(f"결함 {args.fault}번 / run {args.run} 재생 시작 — 총 {n_windows}개 윈도우, "
          f"{args.interval}초 간격, 샘플 {WARMUP_SAMPLE}부터 결함 진행 (Ctrl+C로 중단)")
    print(f"대상 서버: {args.host}\n")

    client = httpx.Client(timeout=10.0)
    try:
        for start in range(0, len(df) - WINDOW_SIZE + 1, args.stride):
            window = values[start:start + WINDOW_SIZE].tolist()
            last_sample = int(samples[start + WINDOW_SIZE - 1])

            resp = client.post(f"{args.host}/anomaly-check", json={"window": window})
            resp.raise_for_status()
            result = resp.json()

            phase = "정상 구간 " if last_sample < WARMUP_SAMPLE else "결함 진행중"
            status = "이상" if result["is_anomaly"] else "정상"
            fault_txt = f" (결함 {result['fault_number']}번 추정)" if result.get("fault_number") else ""
            print(f"[sample {last_sample:>3}/{total_samples}] {phase} | 판정: {status}"
                  f"{fault_txt} | 확신도 {result['confidence']:.2f}")

            time.sleep(args.interval)
        print("\n재생 완료.")
    except KeyboardInterrupt:
        print("\n시뮬레이션 중단됨.")
    except httpx.ConnectError:
        print(f"\n{args.host}에 연결할 수 없습니다. FastAPI 서버(uvicorn)를 먼저 실행하세요.")
        sys.exit(1)
    finally:
        client.close()


if __name__ == "__main__":
    main()
