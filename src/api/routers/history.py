"""
GET /sensor-logs, GET /guide-logs

프론트엔드 "이력 대시보드"용 조회 엔드포인트. anomaly.py/guide.py가 DB에 저장한
로그를 최신순으로 꺼내서 보여준다. 원래 기획서 스펙에는 없던 엔드포인트지만,
이미 쌓이고 있는 로그를 조회할 방법이 없으면 대시보드를 만들 수 없어서 추가함.
"""

from fastapi import APIRouter, Depends
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


@router.get("/guide-logs", response_model=list[GuideRequestLogItem])
def list_guide_logs(limit: int = 50, db: Session = Depends(get_db)):
    rows = db.query(GuideRequestLog).order_by(desc(GuideRequestLog.created_at)).limit(limit).all()
    return rows
