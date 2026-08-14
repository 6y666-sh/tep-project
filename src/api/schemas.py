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
    # xmeas_1..41 + xmv_1..11 값(52개)을 JSON 문자열로 그대로 전달.
    # 굳이 list[float]로 파싱해서 응답하지 않는 이유: 이 필드는 프론트의 설비별
    # 그래프에서만 쓰이고, 서버가 값의 의미를 해석할 일이 없어서 그대로 통과시키는 게
    # 더 단순하다(파싱 책임을 실제로 값을 쓰는 쪽인 프론트로 넘김).
    sensor_values: str | None = None
    resolved: bool = False
    resolved_at: datetime | None = None
    confirmed_fault_number: int | None = None
    # 하네스가 이 이상 건에 대해 자동으로 만들어준(또는 재사용한) 조치가이드.
    # guide_request_log_id만 두면 프론트가 또 API를 한 번 더 불러야 해서,
    # 이력 조회 시점에 아예 내용을 같이 붙여서 내려준다(history.py 참고).
    guide_request_log_id: int | None = None
    guide_text: str | None = None
    guide_confidence: str | None = None
    guide_reference_count: int | None = None

    class Config:
        from_attributes = True  # SQLAlchemy 모델 객체를 그대로 넣을 수 있게 함


class ResolveSensorLogRequest(BaseModel):
    # 0 = 정상(오탐이었음), 1~20 = 실제 결함 번호. 작업자가 상황종료를 누르기 전에
    # 반드시 골라야 하는 값이라 Optional이 아니라 필수 필드로 둔다.
    confirmed_fault_number: int = Field(..., ge=0, le=20, description="작업자가 확인한 실제 결함 번호(0=정상/오탐)")


class ResolveByFaultRequest(BaseModel):
    # 모델이 예측한 fault_number 기준으로 "그 결함으로 아직 미해결인 로그 전부"를
    # 찾아서 한 번에 처리한다 (알림 큐가 결함 유형 단위로 하나의 사고로 묶어서
    # 보여주기 때문 — 자세한 이유는 history.py의 resolve_sensor_logs_by_fault 참고).
    fault_number: int = Field(..., description="일괄 처리할 대상, 모델이 예측했던 결함 번호")
    confirmed_fault_number: int = Field(..., ge=0, le=20, description="작업자가 확인한 실제 결함 번호(0=정상/오탐)")


class GuideRequestLogItem(BaseModel):
    id: int
    created_at: datetime
    fault_description: str
    guide_confidence: str
    reference_count: int
    guide_text: str | None = None

    class Config:
        from_attributes = True
