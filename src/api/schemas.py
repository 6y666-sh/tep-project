"""API 요청/응답 스키마 (pydantic). 기획서 3-4 출력 스펙과 맞춤."""

from datetime import datetime

from pydantic import BaseModel, Field


class AnomalyCheckRequest(BaseModel):
    # 최근 10개 시점 x 52개 변수(xmeas_1~41, xmv_1~11 순서) 윈도우.
    # 예: [[0.25, 3674.0, ..., 41.25], [...], ...] (길이 10짜리 리스트, 각 원소는 길이 52)
    window: list[list[float]] = Field(
        ...,
        description="최근 N개 시점의 센서 값 윈도우. 각 시점은 [xmeas_1..41, xmv_1..11] 순서의 52개 값",
    )


class AnomalyCheckResponse(BaseModel):
    is_anomaly: bool
    fault_number: int | None = Field(None, description="이상으로 판정된 경우에만 추정 결함 번호(1~20)")
    confidence: float = Field(..., description="0~1, 이상일 확신도(하네스 재분석 판단에 사용)")


class GetGuideRequest(BaseModel):
    fault_description: str = Field(..., description="결함 상황을 설명하는 자연어 텍스트")


class ReferenceDoc(BaseModel):
    code: str
    title: str
    year: int
    page: int


class GetGuideResponse(BaseModel):
    guide_text: str
    reference_docs: list[ReferenceDoc]
    confidence: str  # "low" / "high"


class SensorLogItem(BaseModel):
    id: int
    created_at: datetime
    is_anomaly: bool
    fault_number: int | None
    confidence: float

    class Config:
        from_attributes = True  # SQLAlchemy 모델 객체를 그대로 넣을 수 있게 함


class GuideRequestLogItem(BaseModel):
    id: int
    created_at: datetime
    fault_description: str
    guide_confidence: str
    reference_count: int

    class Config:
        from_attributes = True
