"""
센서 로그 / 조치가이드 요청 이력 테이블.

기획서 3-4 스펙: "DB: MySQL (센서 로그, 결함 이력)"에 대응한다.
- SensorLog: /anomaly-check 호출 결과 하나하나를 기록 (센서 로그 + 결함 이력을 겸함)
- GuideRequestLog: /get-guide 호출 이력을 기록 (나중에 "결함이 반복 감지되면
  RAG 재요청" 같은 하네스 로직을 만들 때, 최근 이력을 조회하는 근거 테이블이 됨)
"""

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text
from sqlalchemy.sql import func

from src.db.session import Base


class SensorLog(Base):
    __tablename__ = "sensor_logs"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    is_anomaly = Column(Boolean, nullable=False)
    fault_number = Column(Integer, nullable=True)  # 정상이거나 분류기가 없으면 None
    confidence = Column(Float, nullable=False)
    # 대시보드의 "설비별(반응기/응축기/압축기/분리기/스트리퍼) 그래프"에 쓰려고,
    # 요청받은 윈도우의 마지막 시점(가장 최근 값) 52개를 JSON 문자열로 그대로 저장해둔다.
    # 52개 값을 각각 컬럼으로 쪼개면 테이블이 지저분해지고 스키마 변경도 잦아지므로,
    # 하나의 Text 컬럼에 JSON 배열로 두고 프론트에서 필요한 인덱스만 꺼내 쓰는 방식을 택함.
    sensor_values = Column(Text, nullable=True)
    # 전체화면 긴급 알림 기능용: 이 이상 건이 "작업자가 상황종료 버튼을 눌러 조치
    # 완료로 처리했는지" 추적. is_anomaly만으로는 "지금도 계속 위험한 상태"인지
    # "이미 확인하고 끈 알림"인지 구분이 안 돼서 별도 플래그가 필요했다.
    resolved = Column(Boolean, nullable=False, default=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    # 작업자가 상황종료 시 직접 확인해준 "진짜" 결함 번호(0=정상/오탐, 1~20=결함).
    # 모델이 예측한 fault_number와는 별개 컬럼이다 — 이 둘을 나란히 남겨둬야
    # 나중에 "모델이 맞았는지"를 집계할 수 있고, RandomForest 재학습용 정답
    # 라벨로도 그대로 쓸 수 있다(모델 예측을 정답인 것처럼 덮어쓰면 안 됨).
    confirmed_fault_number = Column(Integer, nullable=True)
    # 재학습 파이프라인용: 이 요청의 윈도우를 학습 때와 같은 방식(mean/std/min/max)으로
    # 요약한 208차원 특징벡터를 "스케일링 전(raw)" 상태로 저장해둔다. sensor_values는
    # 마지막 시점 52개 값만 담아서 대시보드 표시용으로 쓰고, 이건 오직 재학습
    # 스크립트가 원본 학습 데이터(windows.npz)와 같은 형식으로 합칠 수 있게 하려는
    # 용도라 별도 컬럼으로 분리했다. scaler.transform 이전 값을 저장하는 이유는,
    # 나중에 scaler가 바뀌더라도(재학습 시 정규화 기준을 다시 잡아야 할 수도 있음)
    # raw 값만 있으면 언제든 다시 변환할 수 있기 때문이다.
    window_features = Column(Text, nullable=True)
    # 하네스(src/orchestration/harness.py)가 이상 감지 직후 자동으로 조치가이드를
    # 만들어주면(또는 최근에 만든 걸 재사용하면) 그 GuideRequestLog.id를 여기 남긴다.
    # 진짜 FK 제약(ForeignKey)은 안 걸었다 — 이 프로젝트 전체가 두 테이블 사이에
    # DB 레벨 제약 없이 애플리케이션 레벨에서만 참조를 관리하는 방식이라 통일함
    # (MySQL/SQLite 양쪽에서 마이그레이션이 단순해지는 이점도 있음).
    guide_request_log_id = Column(Integer, nullable=True)


class GuideRequestLog(Base):
    __tablename__ = "guide_request_logs"

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    # MySQL은 VARCHAR에 길이 지정이 필수라 명시함 (SQLite는 없어도 됐지만 MySQL은 에러남)
    fault_description = Column(String(1000), nullable=False)
    guide_confidence = Column(String(20), nullable=False)  # "low" / "high"
    reference_count = Column(Integer, nullable=False)
    # Text 타입은 VARCHAR와 달리 길이 제한을 안 걸어도 되고(생성된 가이드가 길 수 있음),
    # 대시보드에서 "최근 조치가이드" 카드에 실제 내용을 보여주려고 저장해둔다.
    guide_text = Column(Text, nullable=True)
