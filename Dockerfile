# 배포용 Dockerfile (멀티스테이지 빌드).
# 1단계: React 프론트엔드를 node 이미지에서 빌드만 하고(최종 이미지엔 node/npm이
#        안 남게), 2단계에서 빌드 결과(dist/)만 파이썬 이미지로 복사해온다.
#        이렇게 하면 최종 이미지에 node_modules 같은 무거운 게 안 남는다.

FROM node:20-slim AS frontend-build
WORKDIR /frontend
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install
COPY frontend/ .
RUN npm run build

FROM python:3.12-slim
WORKDIR /app

# 슬림 이미지 사용 이유: torch 등 무거운 학습용 패키지가 빠진 requirements-api.txt만
# 설치해서 이미지를 가볍게 유지 (풀 이미지 대비 빌드/배포 속도 개선)
COPY requirements-api.txt .
RUN pip install --no-cache-dir -r requirements-api.txt

# 코드 + 이미 학습/구축해둔 결과물(모델, 벡터DB)을 이미지에 그대로 포함.
# .gitignore로 깃에는 안 올라가지만, 배포 이미지엔 실제로 있어야 서빙이 되므로
# 로컬에서 docker build 할 때 이 파일들이 존재해야 한다.
COPY src/ src/
COPY models/ models/
COPY vectorstore/ vectorstore/

# 1단계에서 빌드된 프론트엔드 결과물만 가져옴 (main.py가 frontend/dist를 정적 서빙함)
COPY --from=frontend-build /frontend/dist/ frontend/dist/

EXPOSE 8000

# Railway 등 호스팅 플랫폼이 $PORT 환경변수로 포트를 지정해주므로, 쉘 형식으로
# 써서 환경변수가 치환되게 함 (exec 형식 대괄호 CMD는 환경변수 치환이 안 됨)
CMD uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}
