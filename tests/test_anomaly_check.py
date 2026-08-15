"""
/anomaly-check 엔드포인트 테스트.

실제 학습된 모델(models/)을 그대로 로드해서 쓴다 — 모킹하지 않는 이유는, 이
테스트의 목적이 "API가 모델을 올바르게 호출하고 응답 스펙을 지키는지"뿐 아니라
"실제 모델이 알려진 결함 샘플을 어느 정도는 잡아내는지"까지 같이 검증하려는
것이기 때문이다.
"""

EXPECTED_VARS = 52
WINDOW_SIZE = 10


def test_response_shape(client, sample_windows):
    """정상/이상 여부와 무관하게 응답 스키마(타입)는 항상 지켜져야 한다."""
    window = sample_windows["4"]
    res = client.post("/anomaly-check", json={"window": window})
    assert res.status_code == 200

    body = res.json()
    assert isinstance(body["is_anomaly"], bool)
    assert isinstance(body["confidence"], float)
    assert 0.0 <= body["confidence"] <= 1.0
    # fault_number는 정상 판정이면 None, 이상 판정이면 1~20 사이여야 한다
    if body["is_anomaly"]:
        assert body["fault_number"] is None or 1 <= body["fault_number"] <= 20
    else:
        assert body["fault_number"] is None


def test_known_fault_sample_is_flagged(client, sample_windows):
    """
    fault_number=1 샘플은 이전 검증(대화 로그의 offset=350 스윕)에서 확신도
    1.0으로 안정적으로 잡히는 걸로 확인된 케이스라, 회귀 테스트로 고정해둔다.
    """
    window = sample_windows["1"]
    res = client.post("/anomaly-check", json={"window": window})
    body = res.json()
    assert body["is_anomaly"] is True
    assert body["fault_number"] == 1


def test_wrong_variable_count_rejected(client, sample_windows):
    """윈도우의 각 시점이 52개 값이 아니면 400을 반환해야 한다(500이 아니라)."""
    bad_window = [row[:-1] for row in sample_windows["4"]]  # 51개로 만들어서 깨뜨림
    res = client.post("/anomaly-check", json={"window": bad_window})
    assert res.status_code == 400


def test_anomaly_check_persists_sensor_log(client, sample_windows):
    """호출 결과가 sensor_logs 테이블에 실제로 기록되는지 확인."""
    before = client.get("/sensor-logs?limit=100").json()

    client.post("/anomaly-check", json={"window": sample_windows["1"]})

    after = client.get("/sensor-logs?limit=100").json()
    assert len(after) == len(before) + 1
    assert after[0]["fault_number"] == 1  # 최신순 정렬이라 방금 넣은 게 맨 앞
