"""
센서 로그 / 조치가이드 요청 이력 테이블.

기획서 3-4 스펙: "DB: MySQL (센서 로그, 결함 이력)"에 대응한다.
- SensorLog: /anomaly-check 호출 결과 하나하나를 기록 (센서 로그 + 결함 이력을 겸함)
- GuideRequestLog: /get-guide 호출 이력을 기록 (나중에 "결함이 반복 감지되면
  RAG 재요청" 같은 하네스 로직을 만들 때, 최근 이력을 조회하는 근거 테이블이 됨)
"""

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String
from sqlalchemy.sql import func

from src.db.session import Base


class SensorLog(Base):
    __tablename__ = "sensor_logs"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    is_anomaly = Column(Boolean, nullable=False)
    fault_number = Column(Integer, nullable=True)  # 정상이거나 분류기가 없으면 None
    confidence = Column(Float, nullable=False)


class GuideRequestLog(Base):
    __tablename__ = "guide_request_logs"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    fault_description = Column(String, nullable=False)
    guide_confidence = Column(String, nullable=False)  # "low" / "high"
    reference_count = Column(Integer, nullable=False)
