"""
POST /get-guide

결함 상황 설명을 받아 RAG 파이프라인(검색 + LLM 생성)으로 조치가이드를 반환한다.
실제 검색/생성 로직은 src/rag/generate_guide.py에 이미 구현돼있어 그대로 재사용한다.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.api.schemas import GetGuideRequest, GetGuideResponse
from src.db.models import GuideRequestLog
from src.db.session import get_db
from src.rag.generate_guide import generate_action_guide

router = APIRouter()


@router.post("/get-guide", response_model=GetGuideResponse)
def get_guide(req: GetGuideRequest, db: Session = Depends(get_db)):
    result = generate_action_guide(req.fault_description)

    # 조치가이드 요청 이력 기록 (나중에 "결함 반복 감지 시 RAG 재요청" 하네스 로직에서
    # 이 테이블을 조회해 "최근에 같은 요청이 있었는지" 판단하는 근거로 쓸 수 있다)
    db.add(GuideRequestLog(
        fault_description=req.fault_description,
        guide_confidence=result["confidence"],
        reference_count=len(result["reference_docs"]),
        guide_text=result["guide_text"],
    ))
    db.commit()

    return GetGuideResponse(**result)
