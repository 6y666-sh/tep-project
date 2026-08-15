"""
/sensor-logs 조회 + 상황종료(resolve) 관련 엔드포인트 테스트.

resolve-by-fault(일괄 처리)를 특히 꼼꼼히 본다 — 알림 큐가 "같은 결함으로
아직 미해결인 로그를 한 번에 전부 처리"하는 걸 전제로 프론트가 동작하기 때문에,
여기서 회귀가 생기면 알림이 "상황종료를 눌러도 계속 뜨는" 버그로 바로 이어진다
(과거에 실제로 겪었던 문제).
"""


def _detect(client, sample_windows, key):
    return client.post("/anomaly-check", json={"window": sample_windows[key]}).json()


def test_since_days_filters_old_logs(client, sample_windows):
    """
    since_days는 날짜 기준 필터라 방금 만든 로그(오늘 자)는 어떤 since_days
    값으로도 걸러지지 않고 나와야 한다. (과거 로그를 만들어 넣는 건 created_at이
    server_default라 API로는 못 하니, "최근 것들은 안 걸러진다"는 쪽만 확인)
    """
    _detect(client, sample_windows, "4")
    rows = client.get("/sensor-logs?limit=50&since_days=1").json()
    assert len(rows) >= 1


def test_resolve_single_log(client, sample_windows):
    _detect(client, sample_windows, "1")
    logs = client.get("/sensor-logs?limit=5").json()
    log_id = logs[0]["id"]

    res = client.post(f"/sensor-logs/{log_id}/resolve", json={"confirmed_fault_number": 1})
    assert res.status_code == 200
    body = res.json()
    assert body["resolved"] is True
    assert body["confirmed_fault_number"] == 1


def test_resolve_nonexistent_log_returns_404(client):
    res = client.post("/sensor-logs/999999/resolve", json={"confirmed_fault_number": 0})
    assert res.status_code == 404


def test_resolve_by_fault_clears_entire_backlog(client, sample_windows):
    """
    시뮬레이션 모드처럼 같은 결함이 여러 번 연속 감지된 상황을 재현한다.
    한 번의 resolve-by-fault 호출로 그 결함번호의 미해결 로그가 전부 처리돼야 한다
    — 하나씩만 처리되면 알림 큐가 "상황종료를 눌러도 계속 뜬다"는 버그로 이어진다.
    """
    for _ in range(4):
        _detect(client, sample_windows, "1")  # fault_number=1이 확실히 잡히는 샘플

    unresolved_before = client.get(
        "/sensor-logs?limit=100&unresolved_only=true&oldest_first=true"
    ).json()
    fault1_before = [r for r in unresolved_before if r["fault_number"] == 1]
    assert len(fault1_before) == 4

    res = client.post(
        "/sensor-logs/resolve-by-fault",
        json={"fault_number": 1, "confirmed_fault_number": 1},
    )
    assert res.status_code == 200
    assert len(res.json()) == 4

    unresolved_after = client.get(
        "/sensor-logs?limit=100&unresolved_only=true&oldest_first=true"
    ).json()
    assert all(r["fault_number"] != 1 for r in unresolved_after)


def test_resolve_by_fault_no_match_returns_404(client):
    res = client.post(
        "/sensor-logs/resolve-by-fault",
        json={"fault_number": 7, "confirmed_fault_number": 7},
    )
    assert res.status_code == 404


def test_unresolved_only_excludes_resolved_and_normal(client, sample_windows):
    _detect(client, sample_windows, "1")   # 이상(미해결) -> 대상
    _detect(client, sample_windows, "0")   # 정상 -> 대상 아님

    logs = client.get("/sensor-logs?limit=10").json()
    anomaly_id = next(r["id"] for r in logs if r["is_anomaly"])
    client.post(f"/sensor-logs/{anomaly_id}/resolve", json={"confirmed_fault_number": 1})

    unresolved = client.get("/sensor-logs?unresolved_only=true&limit=100").json()
    assert all(r["is_anomaly"] and not r["resolved"] for r in unresolved)
    assert all(r["id"] != anomaly_id for r in unresolved)
