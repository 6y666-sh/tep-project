"""
DB 연결 설정.

왜 기본값을 SQLite로 했는가:
기획서 스펙은 MySQL이지만, MySQL은 별도 서버 설치/계정 설정이 필요해서 로컬 개발
단계에서 진입장벽이 크다(이 프로젝트에서 Python 버전 문제로도 계속 막혔던 걸 생각하면,
불필요한 설정 단계를 더 늘리고 싶지 않았음). SQLAlchemy를 쓰면 DB 종류가 바뀌어도
모델 코드는 그대로 두고 접속 문자열(DATABASE_URL)만 바꾸면 되므로, 지금은 SQLite로
가볍게 개발하고 배포 시점에 DATABASE_URL만 MySQL 접속 문자열로 바꾸면 된다.
예: mysql+pymysql://user:password@host:3306/tep_db
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tep_logs.db")

# SQLite는 기본적으로 하나의 스레드에서만 연결을 쓰도록 강제하는데, FastAPI는
# 요청마다 다른 스레드를 쓸 수 있어서 이 옵션이 필요하다. MySQL 등 다른 DB는
# 이 옵션 자체를 무시하므로 안 써도 무방하지만, 조건부로 SQLite일 때만 켜준다.
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI 의존성 주입용: 요청마다 세션을 열고, 끝나면 반드시 닫는다."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
