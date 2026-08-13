"""
FastAPI 진입점. 기획서 3-4 스펙의 두 엔드포인트를 하나의 서버로 통합.

실행: uvicorn src.api.main:app --reload --port 8000
문서: 실행 후 http://localhost:8000/docs 에서 Swagger UI로 바로 테스트 가능
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from src.api.routers import anomaly, guide, history
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

# 프론트엔드(React, Vite 개발서버는 기본 5173 포트)에서 이 API를 호출하려면
# 브라우저가 CORS를 막는다. 개발 중엔 로컬호스트 포트 다 열어주고,
# 배포 시엔 프론트를 이 서버가 직접 정적 서빙하니 어차피 같은 origin이라 문제 없음.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(anomaly.router, tags=["anomaly"])
app.include_router(guide.router, tags=["guide"])
app.include_router(history.router, tags=["history"])


@app.get("/health")
def health():
    return {"status": "ok"}


# 프론트엔드 빌드 결과(frontend/dist)를 정적 파일로 서빙.
# 로컬 개발 중엔 이 폴더가 없을 수 있어서 존재할 때만 마운트한다
# (배포용 Dockerfile에서 React 빌드 후 이 경로에 결과물을 넣어줌).
FRONTEND_DIST = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
if os.path.isdir(FRONTEND_DIST):
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
