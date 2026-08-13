"""
검색된 KOSHA GUIDE 조각을 근거로, LLM API를 통해 실제 조치가이드 텍스트를 생성.

왜 Groq인가:
GroqCloud는 신용카드 없이 쓸 수 있는 무료 API 티어를 제공하고(하루 14,400 요청),
OpenAI SDK와 호환되는 인터페이스라 requirements.txt에 이미 있는 openai 패키지로
그대로 쓸 수 있다. 파인튜닝 없이 사전학습 모델 API만 호출한다는 프로젝트 제약에도 맞는다.

왜 "검색 → 생성" 두 단계로 나눴는가 (RAG의 핵심 아이디어):
LLM에게 그냥 "이 결함 대처법 알려줘"라고 물으면, 모델이 학습 당시 알던 일반 지식으로
답하거나 내용을 지어낼(hallucination) 위험이 있다. 대신 실제 KOSHA 지침에서 관련
부분을 먼저 검색해서 그 내용을 근거로만 답하게 하면, 답변이 실제 문서에 기반하고
출처(reference_docs)도 명확히 남길 수 있다.

이 파일이 ingest_kosha.py의 클래스를 다시 정의하는 이유:
스크립트를 어느 위치에서 실행하든(`python src/rag/generate_guide.py`) 안전하게
동작하도록, cross-import 없이 필요한 부분만 자체 포함시켰다.
"""

import os

from dotenv import load_dotenv
from langchain_community.vectorstores import Chroma
from langchain_core.embeddings import Embeddings
from openai import OpenAI

import chromadb.utils.embedding_functions as embedding_functions

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"

PERSIST_DIR = "vectorstore"
COLLECTION_NAME = "kosha_guides"

# 검색된 문서가 질문과 너무 동떨어져 있으면(거리값이 크면) 억지로 답변을
# 생성하지 않기 위한 임계값. chromadb 기본 임베딩(경량 MiniLM) 기준 경험적으로 잡음.
#
# 알려진 한계(면접 대비 메모): 테스트 중 "반응기 압력 상승" 질의에 명백히
# 무관한 "알루미늄 분진 폭발방지" 지침이 거리 0.461로 검색된 사례가 있었다.
# 문제는 이 문서가 진짜 관련 문서들(0.366~0.489)과 거리값이 겹쳐 있어서,
# 임계치를 아무리 조정해도 이 케이스만 골라서 못 거른다는 점이다. 원인은
# 무료 경량 임베딩 모델(MiniLM)이 "공정/안전/폭발/기술지침" 같은 표면적
# 단어 유사도에 끌리고, 세부 주제(압력 vs 분진)까지는 잘 구분 못 하기 때문.
# 개선하려면 OpenAI text-embedding-3-small 같은 고품질 임베딩 API로 교체하면
# 되지만(토큰당 비용 발생), 지금은 베이스라인이라 이 한계를 인지한 채로 진행.
DISTANCE_THRESHOLD = 0.5


class ChromaDefaultEmbeddings(Embeddings):
    def __init__(self):
        self._fn = embedding_functions.DefaultEmbeddingFunction()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [[float(x) for x in v] for v in self._fn(texts)]

    def embed_query(self, text: str) -> list[float]:
        return [float(x) for x in self._fn([text])[0]]


def retrieve_guides(query: str, top_k: int = 5):
    """벡터DB에서 관련 청크 검색 + 최신 지침 우선 로직 적용."""
    embeddings = ChromaDefaultEmbeddings()
    vectordb = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=PERSIST_DIR,
    )
    results = vectordb.similarity_search_with_score(query, k=top_k)

    # 같은 주제(title)의 지침이 여러 버전(연도)으로 검색되면, 최신 연도 것만 남긴다.
    # (원 기획서 3-3: "관련 지침이 여러 건 검색되면 → 최신 지침을 우선하도록 판단")
    best_by_title = {}
    for doc, score in results:
        title = doc.metadata.get("title") or doc.metadata.get("source")
        year = doc.metadata.get("year", 0)
        prev = best_by_title.get(title)
        if prev is None or year > prev[0].metadata.get("year", 0):
            best_by_title[title] = (doc, score)

    # score(거리)는 작을수록 관련도가 높음 → 오름차순 정렬
    return sorted(best_by_title.values(), key=lambda pair: pair[1])


def generate_action_guide(fault_description: str, top_k: int = 5) -> dict:
    """
    결함 상황 설명을 받아 관련 KOSHA 지침을 검색하고, 그 내용을 근거로
    LLM이 조치가이드를 생성하게 한다.

    출력 형식(원 기획서 3-2 스펙과 동일): guide_text, reference_docs
    """
    retrieved = retrieve_guides(fault_description, top_k=top_k)

    # 개별 문서 단위로 거리 임계치를 적용 (예전엔 1등 문서만 검사해서, 관련성 낮은
    # 4~5등 문서까지 그대로 프롬프트에 섞여 들어가 엉뚱한 지침이 답변에 끌려오는
    # 문제가 있었다. 각 문서마다 걸러야 그런 노이즈가 안 들어간다)
    retrieved = [(doc, score) for doc, score in retrieved if score <= DISTANCE_THRESHOLD]

    if not retrieved:
        # 신뢰도 낮음 → 하네스 로직: 답변 생성 대신 재확인 필요 알림
        return {
            "guide_text": (
                "관련 KOSHA 지침을 신뢰할 수 있는 수준으로 찾지 못했습니다. "
                "수동으로 재확인이 필요합니다."
            ),
            "reference_docs": [],
            "confidence": "low",
        }

    context_blocks = []
    reference_docs = []
    for doc, score in retrieved:
        meta = doc.metadata
        page_display = meta.get("page", 0) + 1  # PyPDFLoader의 page는 0-base라 사람이 보기 좋게 +1
        context_blocks.append(
            f"[{meta.get('code')} / {meta.get('title')} ({meta.get('year')}년) p.{page_display}]\n"
            f"{doc.page_content}"
        )
        reference_docs.append({
            "code": meta.get("code"),
            "title": meta.get("title"),
            "year": meta.get("year"),
            "page": page_display,
        })

    context = "\n\n---\n\n".join(context_blocks)

    prompt = f"""당신은 화학공정 안전 관리자를 돕는 조치가이드 생성 시스템입니다.
아래 결함 상황과, 관련된 KOSHA 안전보건기술지침 발췌 내용을 참고해서
현장 작업자가 바로 따라할 수 있는 조치가이드를 작성하세요.

[결함 상황]
{fault_description}

[관련 KOSHA 지침 발췌]
{context}

[작성 지침]
- 반드시 위 지침 내용에 근거해서 작성하고, 지침에 없는 내용을 지어내지 마세요
- 단계별로 명확하게 작성하세요 (1. 2. 3. ...)
- 각 단계 끝에 근거가 된 지침 코드를 [코드] 형태로 표시하세요
"""

    client = OpenAI(api_key=GROQ_API_KEY, base_url=GROQ_BASE_URL)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,  # 안전 지침 생성이라 창의성보다 일관성·정확성을 우선
    )
    guide_text = response.choices[0].message.content

    return {
        "guide_text": guide_text,
        "reference_docs": reference_docs,
        "confidence": "high",
    }


if __name__ == "__main__":
    result = generate_action_guide("반응기 압력이 비정상적으로 상승하고 있습니다.")
    print(result["guide_text"])
    print("\n참고 문서:")
    for ref in result["reference_docs"]:
        print(f"  - {ref['code']} {ref['title']} ({ref['year']}년) p.{ref['page']}")
