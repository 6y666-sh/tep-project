# TEP 화학공정 이상탐지 + RAG 조치가이드

## 폴더 구조
```
tep-project/
├── data/
│   ├── raw/            # Kaggle 원본 CSV (git 미포함)
│   └── processed/       # 전처리된 데이터 (git 미포함)
├── models/               # 학습된 이상탐지 모델 (git 미포함)
├── vectorstore/          # Chroma 벡터DB 저장소 (git 미포함)
├── docs/kosha_guides/    # KOSHA GUIDE 원문 (git 미포함)
├── notebooks/            # EDA/실험용 노트북
├── src/
│   ├── data_pipeline/    # 로드·전처리·시퀀스 윈도우
│   ├── anomaly_detection/# 베이스라인 모델 학습/평가
│   ├── rag/               # 문서 인제스트·검색·생성
│   ├── orchestration/     # 신뢰도/우선순위/재요청 판단 로직
│   ├── api/                # FastAPI 서버
│   └── db/                  # MySQL 모델/세션
├── tests/
├── requirements.txt
└── .gitignore
```

## 진행 순서 (커밋 단위 권장)
1. 뼈대 (본 커밋)
2. 데이터 로드 및 전처리 (`src/data_pipeline`)
3. 베이스라인 이상탐지 모델 (`src/anomaly_detection`)
4. KOSHA 문서 → 벡터DB 구축 (`src/rag`)
5. RAG 검색+생성 파이프라인 (`src/rag`)
6. FastAPI 통합 서빙 (`src/api`)
7. 하네스 판단 로직 고도화 (`src/orchestration`)
