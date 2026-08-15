"""
하네스(src/orchestration/harness.py) 로직 테스트.

generate_action_guide는 항상 mock 처리한다 — 실제 Groq API를 호출하면 (1) 테스트가
네트워크에 의존하게 되고 (2) API 키/요금이 필요해지고 (3) 응답이 매번 달라져서
assert가 불안정해진다. 여기서 검증하려는 건 "LLM이 뭐라고 답하냐"가 아니라
"하네스가 언제 LLM을 부르고 언제 안 부르는지"이므로 mock으로 충분하다.

run_harness_for_log_id를 직접 호출한다(엔드포인트를 통하지 않고) — /anomaly-check는
이걸 BackgroundTasks로 비동기로 예약만 하기 때문에, TestClient로 호출하면 응답
시점에 하네스가 이미 다 끝났다는 보장이 없다(Starlette가 백그라운드 태스크를
응답 이후 실행하긴 하지만, 테스트를 그 타이밍에 의존하게 만들고 싶지 않았음).
"""

from unittest.mock import patch

from src.db.models import GuideRequestLog, SensorLog
from src.db.session import SessionLocal
from src.orchestration.harness import fault_description_for, run_harness_for_log_id

FAKE_GUIDE = {
    "guide_text": "1. 밸브를 확인하세요. [TEST-CODE]",
    "reference_docs": [{"code": "TEST-CODE", "title": "테스트 지침", "year": 2024, "page": 1}],
    "confidence": "high",
}


def _insert_sensor_log(db, fault_number, confidence, resolved=False):
    log = SensorLog(is_anomaly=True, fault_number=fault_number, confidence=confidence, resolved=resolved)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def test_low_confidence_skips_auto_guide():
    db = SessionLocal()
    try:
        log = _insert_sensor_log(db, fault_number=9, confidence=0.1)  # AUTO_GUIDE_MIN_CONFIDENCE(0.3) 미만
    finally:
        db.close()

    with patch("src.orchestration.harness.generate_action_guide", side_effect=AssertionError("호출되면 안 됨")):
        run_harness_for_log_id(log.id)

    db = SessionLocal()
    try:
        refreshed = db.query(SensorLog).filter(SensorLog.id == log.id).first()
        assert refreshed.guide_request_log_id is None
    finally:
        db.close()


def test_high_confidence_generates_and_links_guide():
    db = SessionLocal()
    try:
        log = _insert_sensor_log(db, fault_number=4, confidence=0.9)
    finally:
        db.close()

    with patch("src.orchestration.harness.generate_action_guide", return_value=FAKE_GUIDE) as mocked:
        run_harness_for_log_id(log.id)
        mocked.assert_called_once()

    db = SessionLocal()
    try:
        refreshed = db.query(SensorLog).filter(SensorLog.id == log.id).first()
        assert refreshed.guide_request_log_id is not None
        guide = db.query(GuideRequestLog).filter(GuideRequestLog.id == refreshed.guide_request_log_id).first()
        assert guide.guide_text == FAKE_GUIDE["guide_text"]
    finally:
        db.close()


def test_repeated_fault_within_cooldown_reuses_guide_no_second_llm_call():
    # id를 세션이 살아있는 동안(같은 db 안에서) 바로 정수로 뽑아둔다 — SensorLog
    # 객체를 세션 close() 이후까지 들고 있다가 .id를 읽으면, 두 번째 insert의
    # commit()이 첫 번째 객체의 속성까지 expire시켜서(SQLAlchemy 기본 동작)
    # DetachedInstanceError가 난다. 이건 하네스 로직과 무관한 테스트 코드
    # 자체의 세션 관리 문제라, 아예 id만 뽑아 쓰는 걸로 피해간다.
    db = SessionLocal()
    try:
        log1_id = _insert_sensor_log(db, fault_number=4, confidence=0.9).id
        log2_id = _insert_sensor_log(db, fault_number=4, confidence=0.9).id  # 같은 결함, 곧바로 재감지
    finally:
        db.close()

    with patch("src.orchestration.harness.generate_action_guide", return_value=FAKE_GUIDE) as mocked:
        run_harness_for_log_id(log1_id)
        run_harness_for_log_id(log2_id)
        # 시뮬레이션 모드처럼 같은 결함이 연달아 잡혀도, 쿨다운 안에서는 LLM을
        # 딱 한 번만 불러야 한다 — 두 번째부터는 기존 가이드를 재사용해야 함.
        assert mocked.call_count == 1

    db = SessionLocal()
    try:
        r1 = db.query(SensorLog).filter(SensorLog.id == log1_id).first()
        r2 = db.query(SensorLog).filter(SensorLog.id == log2_id).first()
        assert r1.guide_request_log_id == r2.guide_request_log_id
        assert db.query(GuideRequestLog).count() == 1
    finally:
        db.close()


def test_different_fault_numbers_each_get_own_guide():
    db = SessionLocal()
    try:
        log1_id = _insert_sensor_log(db, fault_number=4, confidence=0.9).id
        log2_id = _insert_sensor_log(db, fault_number=5, confidence=0.9).id
    finally:
        db.close()

    with patch("src.orchestration.harness.generate_action_guide", return_value=FAKE_GUIDE) as mocked:
        run_harness_for_log_id(log1_id)
        run_harness_for_log_id(log2_id)
        assert mocked.call_count == 2


def test_fault_description_is_deterministic():
    """같은 fault_number는 항상 같은 문장을 만들어야 dedup 매칭이 성립한다."""
    assert fault_description_for(4) == fault_description_for(4)
    assert fault_description_for(4) != fault_description_for(5)
