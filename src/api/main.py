"""
FastAPI 진입점. 기획서 3-4 스펙의 두 엔드포인트를 하나의 서버로 통합.

실행: uvicorn src.api.main:app --reload --port 8000
문서: 실행 후 http://localhost:8000/docs 에서 Swagger UI로 바로 테스트 가능
"""

from fastapi import FastAPI

from src.api.routers import anomaly, guide
from src.db.session import Base, engine

# 앱 시작 시 테이블이 없으면 생성 (SQLite 기준 매우 가벼운 마이그레이션 방식.
# 운영 환경에서는 alembic 같은 마이그레이션 도구를 쓰는 게 정석이지만,
# 베이스라인 단계에서는 이 정도로 충분함)
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="TEP 화학공정 이상탐지 + RAG 조치가이드 API",
    description="Tennessee Eastman Process 이상탐지와 KOSHA GUIDE 기반 조치가이드 생성을 제공하는 API",
    version="0.1.0",
)

app.include_router(anomaly.router, tags=["anomaly"])
app.include_router(guide.router, tags=["guide"])


@app.get("/health")
def health():
    return {"status": "ok"}
