"""
GET /sensor-logs, GET /guide-logs

프론트엔드 "이력 대시보드"용 조회 엔드포인트. anomaly.py/guide.py가 DB에 저장한
로그를 최신순으로 꺼내서 보여준다. 원래 기획서 스펙에는 없던 엔드포인트지만,
이미 쌓이고 있는 로그를 조회할 방법이 없으면 대시보드를 만들 수 없어서 추가함.
"""

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.api.schemas import (
    GuideRequestLogItem,
    ResolveByFaultRequest,
    ResolveSensorLogRequest,
    SensorLogItem,
)
from src.db.models import GuideRequestLog, SensorLog
from src.db.session import get_db

router = APIRouter()


def _attach_guides(rows: list[SensorLog], db: Session) -> list[dict]:
    """
    하네스가 sensor_log.guide_request_log_id에 연결해둔 조치가이드 내용을
    같이 붙여서 내려준다. 프론트가 이상 로그 하나를 볼 때마다 가이드를 또
    따로 요청하지 않아도 되게 하려는 목적이다. row마다 따로 쿼리하면 N+1이
    되니, 필요한 guide_request_log_id들을 모아 한 번의 IN 쿼리로 가져온다.
    """
    guide_ids = {row.guide_request_log_id for row in rows if row.guide_request_log_id is not None}
    guides_by_id = {}
    if guide_ids:
        guide_rows = db.query(GuideRequestLog).filter(GuideRequestLog.id.in_(guide_ids)).all()
        guides_by_id = {g.id: g for g in guide_rows}

    result = []
    for row in rows:
        guide = guides_by_id.get(row.guide_request_log_id)
        result.append({
            "id": row.id,
            "created_at": row.created_at,
            "is_anomaly": row.is_anomaly,
            "fault_number": row.fault_number,
            "confidence": row.confidence,
            "sensor_values": row.sensor_values,
            "resolved": row.resolved,
            "resolved_at": row.resolved_at,
            "confirmed_fault_number": row.confirmed_fault_number,
            "guide_request_log_id": row.guide_request_log_id,
            "guide_text": guide.guide_text if guide else None,
            "guide_confidence": guide.guide_confidence if guide else None,
            "guide_reference_count": guide.reference_count if guide else None,
        })
    return result


@router.get("/sensor-logs", response_model=list[SensorLogItem])
def list_sensor_logs(
    limit: int = 50,
    since_days: int | None = None,
    unresolved_only: bool = False,
    oldest_first: bool = False,
    db: Session = Depends(get_db),
):
    """
    since_days: 지정하면 "최근 N일 이내" 로그만 본다 (limit과 별개 조건, AND로 적용).
    대시보드의 "최근 감지된 결함 유형" 카드가 이 파라미터를 쓴다 — 반복적으로
    같은 결함이 발생하는 설비를 찾아내려는 목적인데, 그냥 limit(최근 N건)만
    쓰면 요청이 몰리는 시기(예: 시뮬레이션 모드)엔 몇 분 만에 지난 데이터가
    밀려나버려서 "최근 N일"이라는 의미가 사라진다. 날짜 기준으로 따로 걸러야
    "이 설비가 이번 달 내내 반복적으로 이상하다"는 패턴을 놓치지 않는다.

    unresolved_only + oldest_first: 프론트 알림 큐(App.jsx)가 쓴다. "아직 상황종료
    안 한 이상"만, 발생한 순서대로(오래된 것부터) 가져와야 대기열을 선입선출로
    보여줄 수 있다 — desc(최신순)로 받아서 프론트에서 뒤집으면, limit에 걸려
    잘려나간 뒷부분(오래된 미해결 건)이 아예 안 보이는 문제가 생길 수 있다.
    """
    query = db.query(SensorLog)
    if since_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=since_days)
        query = query.filter(SensorLog.created_at >= cutoff)
    if unresolved_only:
        query = query.filter(SensorLog.is_anomaly.is_(True), SensorLog.resolved.is_(False))
    order = SensorLog.created_at.asc() if oldest_first else desc(SensorLog.created_at)
    rows = query.order_by(order).limit(limit).all()
    return _attach_guides(rows, db)


@router.post("/sensor-logs/{log_id}/resolve", response_model=SensorLogItem)
def resolve_sensor_log(log_id: int, req: ResolveSensorLogRequest, db: Session = Depends(get_db)):
    """전체화면 긴급 알림에서 "상황종료" 버튼을 눌렀을 때 호출.

    실시간 센서 스트리밍이 없는 이 프로젝트 구조상 "결함이 실제로 해소됐는지"를
    시스템이 스스로 알 방법이 없다(다음 판정이 들어와야 정상/이상을 다시 알 수
    있음). 그래서 "조치가 끝났다"는 판단은 작업자가 직접 내리고, 시스템은 그
    확인 시각만 기록해서 알림을 닫아주는 방식으로 설계했다.

    confirmed_fault_number를 필수로 받는 이유: 모델의 예측(fault_number)이
    맞았는지 작업자가 직접 확인해서 정답 라벨을 남겨야, 나중에 이 기록을
    RandomForest 재학습용 데이터로 그대로 쓸 수 있다(active learning 루프의
    "사람이 라벨을 고쳐주는" 단계에 해당).
    """
    row = db.query(SensorLog).filter(SensorLog.id == log_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="해당 로그를 찾을 수 없습니다.")
    row.resolved = True
    row.resolved_at = datetime.now(timezone.utc)
    row.confirmed_fault_number = req.confirmed_fault_number
    db.commit()
    db.refresh(row)
    return _attach_guides([row], db)[0]


@router.post("/sensor-logs/resolve-by-fault", response_model=list[SensorLogItem])
def resolve_sensor_logs_by_fault(req: ResolveByFaultRequest, db: Session = Depends(get_db)):
    """
    같은 결함(fault_number)으로 아직 상황종료 안 한 로그를 한 번에 전부 처리한다.

    왜 필요한가: 시뮬레이션 모드는 3초마다 새 윈도우를 보내는데, 같은 결함이
    한동안 계속되면(실제 TEP 결함 발생 구간이 보통 그렇다) 매 윈도우마다 새
    SensorLog 행이 생기고 전부 "미해결 이상"으로 쌓인다. 예전처럼 한 번에
    한 건(id 하나)씩만 상황종료 처리하면, 작업자가 방금 확인한 결함이 바로
    다음 폴링에서 또 뜬다 — 사실은 "같은 사고"인데 사고 하나당 알림이 수십 개
    쌓이는 셈. 여기서는 "그 결함 유형 전체"를 하나의 사고로 보고 한 번에 닫는다.

    resolve_sensor_log(단건)는 이력 화면 등에서 과거 로그 하나를 개별적으로
    고쳐야 할 때를 위해 남겨두고, 실시간 알림(AlertOverlay)은 이 엔드포인트를 쓴다.
    """
    rows = (
        db.query(SensorLog)
        .filter(
            SensorLog.is_anomaly.is_(True),
            SensorLog.resolved.is_(False),
            SensorLog.fault_number == req.fault_number,
        )
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail="해당 결함으로 아직 처리되지 않은 로그가 없습니다.")

    now = datetime.now(timezone.utc)
    for row in rows:
        row.resolved = True
        row.resolved_at = now
        row.confirmed_fault_number = req.confirmed_fault_number
    db.commit()
    for row in rows:
        db.refresh(row)
    return _attach_guides(rows, db)


@router.get("/guide-logs", response_model=list[GuideRequestLogItem])
def list_guide_logs(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.query(GuideRequestLog).order_by(desc(GuideRequestLog.created_at)).limit(limit).all()
    return rows
