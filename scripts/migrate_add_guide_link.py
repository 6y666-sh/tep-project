"""
DB 마이그레이션: sensor_logs 테이블에 guide_request_log_id 컬럼 추가.

하네스(src/orchestration/harness.py)가 이상탐지 로그와, 그걸 보고 자동으로
만든(또는 재사용한) 조치가이드를 서로 연결해두는 데 쓰는 컬럼이다. 이전
migrate_add_*.py 스크립트들과 같은 이유(create_all()은 이미 있는 테이블에
컬럼을 추가해주지 않음)로 필요하다.

실행 방법 (venv 활성화 후, 프로젝트 루트에서):
    python scripts/migrate_add_guide_link.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text  # noqa: E402

from src.db.session import engine  # noqa: E402


def main():
    inspector = inspect(engine)

    if "sensor_logs" not in inspector.get_table_names():
        print("sensor_logs 테이블이 아직 없습니다. "
              "서버를 한 번 실행하면 create_all()이 알아서 만들어줍니다.")
        return

    existing_columns = {col["name"] for col in inspector.get_columns("sensor_logs")}

    if "guide_request_log_id" in existing_columns:
        print("guide_request_log_id 컬럼이 이미 존재합니다. 마이그레이션 불필요.")
        return

    dialect = engine.dialect.name
    if dialect == "mysql":
        ddl = "ALTER TABLE sensor_logs ADD COLUMN guide_request_log_id INT NULL"
    elif dialect == "sqlite":
        ddl = "ALTER TABLE sensor_logs ADD COLUMN guide_request_log_id INTEGER"
    else:
        raise RuntimeError(f"지원하지 않는 DB 종류: {dialect}")

    with engine.begin() as conn:
        conn.execute(text(ddl))

    print(f"guide_request_log_id 컬럼 추가 완료 ({dialect}).")


if __name__ == "__main__":
    main()
