"""
pytest 공통 픽스처.

핵심 설계 원칙: 테스트는 절대 실제 DB(로컬 MySQL이든 배포용이든)를 건드리면 안
된다. 그래서 이 파일이 가장 먼저(다른 어떤 프로젝트 코드보다도 먼저) DATABASE_URL을
임시 SQLite 파일로 강제 설정한다 — src/db/session.py가 os.getenv("DATABASE_URL")을
"모듈을 import하는 시점"에 딱 한 번 읽기 때문에, import보다 먼저 환경변수를
설정해둬야 한다(늦게 설정하면 이미 실제 DATABASE_URL로 엔진이 만들어진 뒤라 소용없음).
"""

import os
import sys
import tempfile

# 프로젝트 루트를 sys.path에 넣어야 `from src...` import가 된다 (scripts/*.py와 동일한 패턴)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_TMP_DB_FD, _TMP_DB_PATH = tempfile.mkstemp(suffix=".db", prefix="tep_test_")
os.close(_TMP_DB_FD)
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP_DB_PATH}"

import json  # noqa: E402

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from src.api.main import app  # noqa: E402
from src.db.session import Base, SessionLocal, engine  # noqa: E402

Base.metadata.create_all(bind=engine)

SAMPLE_WINDOWS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "frontend", "src", "assets", "sample_windows.json",
)


def pytest_sessionfinish(session, exitstatus):
    """전체 테스트 세션이 끝나면 임시 DB 파일 삭제."""
    try:
        os.remove(_TMP_DB_PATH)
    except OSError:
        pass


@pytest.fixture(autouse=True)
def _clean_tables():
    """
    테스트마다 테이블을 비워서 서로 영향 안 주게 한다(순서 의존적인 테스트 방지).
    스키마 자체는 세션 시작할 때 한 번만 만들면 되니 drop/create 대신 DELETE만 한다
    (SQLite에서 훨씬 빠름).
    """
    yield
    db = SessionLocal()
    try:
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
    finally:
        db.close()


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture(scope="session")
def sample_windows():
    """
    실제 TEP 데이터에서 뽑은 결함별 샘플 윈도우 (frontend가 "이상탐지 테스트"
    화면에서 쓰는 것과 같은 파일). key는 "0"(정상)~"20"(결함 20번) 문자열.
    합성 데이터 대신 이걸 쓰는 이유: 진짜 모델이 실제로 그 결함을 잡아내는지까지
    검증할 수 있어서, 단순 API 스펙 테스트보다 신뢰도가 높다.
    """
    with open(SAMPLE_WINDOWS_PATH, encoding="utf-8") as f:
        return json.load(f)
