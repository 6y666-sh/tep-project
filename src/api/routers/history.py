"""
GET /sensor-logs, GET /guide-logs

프론트엔드 "이력 대시보드"용 조회 엔드포인트. anomaly.py/guide.py가 DB에 저장한
로그를 최신순으로 꺼내서 보여준다. 원래 기획서 스펙에는 없던 엔드포인트지만,
이미 쌓이고 있는 로그를 조회할 방법이 없으면 대시보드를 만들 수 없어서 추가함.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from src.api.schemas import GuideRequestLogItem, SensorLogItem
from src.db.models import GuideRequestLog, SensorLog
from src.db.session import get_db

router = APIRouter()


@router.get("/sensor-logs", response_model=list[SensorLogItem])
def list_sensor_logs(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.query(SensorLog).order_by(desc(SensorLog.created_at)).limit(limit).all()
    return rows


@router.post("/sensor-logs/{log_id}/resolve", response_model=SensorLogItem)
def resolve_sensor_log(log_id: int, db: Session = Depends(get_db)):
    """전체화면 긴급 알림에서 "상황종료" 버튼을 눌렀을 때 호출.

    실시간 센서 스트리밍이 없는 이 프로젝트 구조상 "결함이 실제로 해소됐는지"를
    시스템이 스스로 알 방법이 없다(다음 판정이 들어와야 정상/이상을 다시 알 수
    있음). 그래서 "조치가 끝났다"는 판단은 작업자가 직접 내리고, 시스템은 그
    확인 시각만 기록해서 알림을 닫아주는 방식으로 설계했다.
    """
    row = db.query(SensorLog).filter(SensorLog.id == log_id).first()
    if row is None:
        raise HTTPException(status_code=404, detail="해당 로그를 찾을 수 없습니다.")
    row.resolved = True
    row.resolved_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return row


@router.get("/guide-logs", response_model=list[GuideRequestLogItem])
def list_guide_logs(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.query(GuideRequestLog).order_by(desc(GuideRequestLog.created_at)).limit(limit).all()
    return rows
