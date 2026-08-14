"""
하네스(orchestration) 로직: 이상탐지 결과를 보고 조치가이드 생성 파이프라인을
자동으로 호출할지 판단한다.

지금까지는 /anomaly-check(이상탐지)와 /get-guide(RAG 조치가이드)가 완전히
분리돼 있었다 — 이상이 감지돼도 작업자가 직접 "조치가이드 생성" 메뉴에서
결함 설명을 타이핑해야만 가이드가 나왔다. 이 모듈이 그 둘을 연결하는 판단
계층이다(README 로드맵 7번 "하네스 판단 로직 고도화"에 해당). 두 가지를
판단한다:

1. confidence가 낮으면 가이드를 자동 생성하지 않는다 — 결함 유형(fault_number)
   자체가 RandomForest의 저신뢰 추정일 수 있는데, 틀린 결함 유형으로 만든
   조치가이드는 오히려 위험하다(엉뚱한 지침으로 작업자를 유도할 수 있음).
   이 경우엔 자동 생성을 건너뛰고, 작업자가 상황종료 시 직접 확인한 뒤
   필요하면 "조치가이드 생성" 메뉴에서 수동으로 만들면 된다.
2. 같은 결함이 짧은 시간 안에 반복 감지돼도(시뮬레이션 모드처럼 3초 간격으로
   같은 결함이 계속 잡히는 경우), 이미 최근에 만들어둔 가이드가 있으면
   재사용하고 LLM을 다시 호출하지 않는다 — 무료 API라도 요청 한도가 있고
   (Groq 하루 14,400 요청), 어차피 같은 결함이면 같은 지침이 나오므로
   호출을 반복하는 건 낭비다. 대신 기존 가이드를 이번 이상 로그에도 연결해준다.

둘 다 통과해야 실제로 RAG 파이프라인(generate_action_guide, LLM 호출 발생)을
불러서 새 조치가이드를 만들고 저장한다.

/anomaly-check가 이 로직을 어떻게 호출하는지는 src/api/routers/anomaly.py 참고
— FastAPI BackgroundTasks로 응답 이후 비동기로 돌려서, LLM 호출 지연이 이상탐지
API 자체의 응답 속도에 영향을 주지 않게 했다.
"""

from datetime import datetime, timedelta, timezone

from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.db.models import GuideRequestLog, SensorLog
from src.db.session import SessionLocal
from src.rag.generate_guide import generate_action_guide

# frontend/src/faultNames.js와 같은 매핑이다. 프론트/백엔드가 완전히 분리된
# 스택이라 코드를 공유할 방법이 없어서 수동으로 동기화한다 — 결함 이름을
# 바꾸면 두 파일 다 고쳐야 한다.
FAULT_NAMES = {
    1: "A/C 공급비 이상 (Step)",
    2: "B 성분 조성 이상 (Step)",
    3: "D 공급 온도 이상 (Step)",
    4: "반응기 냉각수 입구온도 이상 (Step)",
    5: "응축기 냉각수 입구온도 이상 (Step)",
    6: "A 공급 유실 (Step)",
    7: "C 헤더 압력 손실 (Step)",
    8: "A/B/C 공급 조성 변동 (Random)",
    9: "D 공급 온도 변동 (Random)",
    10: "C 공급 온도 변동 (Random)",
    11: "반응기 냉각수 입구온도 변동 (Random)",
    12: "응축기 냉각수 입구온도 변동 (Random)",
    13: "반응 속도 이상 (Slow Drift)",
    14: "반응기 냉각수 밸브 고착",
    15: "응축기 냉각수 밸브 고착",
}

# anomaly.py의 _score_to_confidence와 같은 0~1 스케일의 confidence를 기준으로 한다.
# 정상/이상 판정(threshold_percentile=40) 자체는 미탐을 줄이려고 관대하게 잡았지만,
# 거기서 한발 더 나가 "어떤 결함인지"까지 자동으로 문서를 찾아 조치를 지시하는
# 단계는 더 신중해야 한다고 봐서, 이 문턱은 별도로 더 보수적으로(0.3) 잡았다.
# 엄밀한 통계적 최적값이 아니라 휴리스틱이다.
AUTO_GUIDE_MIN_CONFIDENCE = 0.3

# 같은 결함 설명으로 이 시간 안에 이미 가이드를 만든 적 있으면 새로 만들지 않고 재사용한다.
DEDUP_COOLDOWN_MINUTES = 15


def fault_description_for(fault_number: int) -> str:
    """fault_number를 RAG 검색 쿼리로 쓸 자연어 문장으로 바꾼다."""
    name = FAULT_NAMES.get(fault_number, f"결함 {fault_number}번 (미상)")
    return f"{name} 결함이 감지되었습니다. 확인 및 조치 방법을 알려주세요."


def run_harness(db: Session, sensor_log: SensorLog) -> None:
    """
    실제 판단 로직. 주어진 세션 안에서 sensor_log.guide_request_log_id를 채워주고,
    필요하면 새 GuideRequestLog를 만들어 db.add한다. commit은 호출자 책임이다
    (백그라운드 태스크에서 부르는 run_harness_for_log_id가 커밋까지 담당).
    """
    if not sensor_log.is_anomaly or sensor_log.fault_number is None:
        return

    # 1) confidence 게이트: 결함 유형 추정이 못 미더우면 자동 생성 안 함
    if sensor_log.confidence < AUTO_GUIDE_MIN_CONFIDENCE:
        return

    description = fault_description_for(sensor_log.fault_number)

    # 2) 중복 방지: 최근 쿨다운 안에 같은 결함으로 이미 만든 가이드가 있으면 재사용
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=DEDUP_COOLDOWN_MINUTES)
    existing = (
        db.query(GuideRequestLog)
        .filter(GuideRequestLog.fault_description == description)
        .filter(GuideRequestLog.created_at >= cutoff)
        .order_by(desc(GuideRequestLog.created_at))
        .first()
    )
    if existing is not None:
        sensor_log.guide_request_log_id = existing.id
        return

    # 3) 실제 RAG 파이프라인 호출 (여기서만 LLM 요청이 발생함)
    result = generate_action_guide(description)
    guide_log = GuideRequestLog(
        fault_description=description,
        guide_confidence=result["confidence"],
        reference_count=len(result["reference_docs"]),
        guide_text=result["guide_text"],
    )
    db.add(guide_log)
    db.flush()  # guide_log.id를 확보하려고 flush (commit은 호출자가)
    sensor_log.guide_request_log_id = guide_log.id


def run_harness_for_log_id(sensor_log_id: int) -> None:
    """
    FastAPI BackgroundTasks 전용 진입점. 요청 스코프 세션이 이미 닫힌 뒤에
    실행되므로, 여기서 독립적인 세션을 새로 열고 닫는다.
    """
    db = SessionLocal()
    try:
        sensor_log = db.query(SensorLog).filter(SensorLog.id == sensor_log_id).first()
        if sensor_log is None:
            return
        run_harness(db, sensor_log)
        db.commit()
    except Exception as e:  # noqa: BLE001
        # 백그라운드 태스크라 예외가 나도 /anomaly-check 응답엔 영향이 없다.
        # 그냥 삼키면 원인 추적이 안 되니 최소한 로그는 남긴다(LLM API 장애 등
        # 하네스 쪽 문제가 이상탐지 자체를 절대 막아선 안 된다는 설계 원칙).
        print(f"[harness] sensor_log_id={sensor_log_id} 처리 중 오류: {e}")
        db.rollback()
    finally:
        db.close()
