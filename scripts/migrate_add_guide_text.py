"""
DB 마이그레이션: guide_request_logs 테이블에 guide_text 컬럼 추가.

왜 필요한가:
SQLAlchemy의 Base.metadata.create_all()은 "없는 테이블"만 새로 만들 뿐,
이미 존재하는 테이블에 컬럼을 추가(ALTER TABLE)해주지는 않는다.
GuideRequestLog 모델에 guide_text 컬럼을 나중에 추가했는데, 이미 MySQL에
guide_request_logs 테이블이 만들어져 있는 상태라면 create_all()은 아무 것도
하지 않는다. 그 상태로 서버가 INSERT를 시도하면 "Unknown column 'guide_text'"
에러가 난다.

정식 프로젝트라면 Alembic 같은 마이그레이션 도구를 쓰지만, 이 프로젝트 규모에서는
과하다고 판단해서 필요한 순간에만 쓰는 1회성 스크립트로 대신한다. 컬럼이 이미
있으면 조용히 넘어가도록 처리해서, 여러 번 실행해도 안전하다(idempotent).

실행 방법 (venv 활성화 후, 프로젝트 루트에서):
    python scripts/migrate_add_guide_text.py
"""

import os
import sys

# python scripts/xxx.py로 실행하면 sys.path[0]이 scripts/ 폴더가 되어서
# "src" 패키지를 못 찾는다. 프로젝트 루트를 sys.path에 직접 추가해준다.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text  # noqa: E402

from src.db.session import engine  # noqa: E402


def main():
    inspector = inspect(engine)

    if "guide_request_logs" not in inspector.get_table_names():
        print("guide_request_logs 테이블이 아직 없습니다. "
              "서버를 한 번 실행하면 create_all()이 알아서 만들어줍니다.")
        return

    existing_columns = {col["name"] for col in inspector.get_columns("guide_request_logs")}

    if "guide_text" in existing_columns:
        print("guide_text 컬럼이 이미 존재합니다. 마이그레이션 불필요.")
        return

    dialect = engine.dialect.name
    if dialect == "mysql":
        ddl = "ALTER TABLE guide_request_logs ADD COLUMN guide_text TEXT NULL"
    elif dialect == "sqlite":
        ddl = "ALTER TABLE guide_request_logs ADD COLUMN guide_text TEXT"
    else:
        raise RuntimeError(f"지원하지 않는 DB 종류: {dialect}")

    with engine.begin() as conn:
        conn.execute(text(ddl))

    print(f"guide_text 컬럼 추가 완료 ({dialect}).")


if __name__ == "__main__":
    main()
