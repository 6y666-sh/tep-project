"""
왜 langchain을 썼는가:
PDF 로딩(PyPDFLoader), 청크 분할(RecursiveCharacterTextSplitter), 벡터DB 연동(Chroma
래퍼)을 langchain이 표준화된 인터페이스로 제공한다. 직접 구현해도 되지만(이전 버전
참고), 업계에서 RAG 파이프라인을 짤 때 사실상 표준으로 쓰이는 프레임워크라 채택함.
다음 단계(4단계: 검색+생성 체인)에서도 이어서 langchain을 사용할 예정.

왜 sentence-transformers 대신 chromadb 기본 임베딩 함수를 langchain에 감싸서 쓰는가:
sentence-transformers는 내부적으로 torch가 필요한데, torch는 아직 Python 3.14용
wheel이 없어 설치가 안 된다. chromadb에 내장된 기본 임베딩 함수(onnxruntime 기반
all-MiniLM-L6-v2)는 torch 없이 동작하므로, 이를 langchain의 Embeddings 인터페이스에
맞게 얇게 감싸는 어댑터 클래스(ChromaDefaultEmbeddings)를 만들어 사용한다.

왜 RecursiveCharacterTextSplitter인가:
문장/문단 단위 구분자(줄바꿈 등)를 우선적으로 존중하면서 자르기 때문에, 단순
글자 수로만 자르는 방식보다 청크 중간에 문장이 뚝 끊길 확률이 낮다.
"""

import glob
import os
import re

import chromadb.utils.embedding_functions as embedding_functions
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import Chroma
from langchain_core.embeddings import Embeddings

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:  # 구버전 langchain 호환
    from langchain.text_splitter import RecursiveCharacterTextSplitter

KOSHA_DIR = "docs/kosha_guides"
PERSIST_DIR = "vectorstore"
COLLECTION_NAME = "kosha_guides"

CHUNK_SIZE = 800     # 청크 하나의 글자 수 (한국어 기준, 문단 몇 개 정도의 분량)
CHUNK_OVERLAP = 150  # 청크 간 겹치는 글자 수 (문장이 청크 경계에서 잘려 문맥이 끊기는 걸 완화)

# KOSHA 공식 코드는 "P-101-2021"처럼 카테고리-번호-연도 형식이라, 코드 자체에서
# 연도(마지막 4자리)를 뽑아낸다. 파일명 규칙: "코드_제목.pdf"
FILENAME_PATTERN = re.compile(r"^(?P<code>[A-Za-z]+-\d+-(?P<year>\d{4}))_(?P<title>.+)$")


class ChromaDefaultEmbeddings(Embeddings):
    """
    chromadb의 기본 임베딩 함수(onnxruntime, MiniLM-L6, torch 불필요)를
    langchain의 Embeddings 인터페이스에 맞게 감싸는 어댑터.
    langchain의 Chroma/검색 관련 클래스들은 이 인터페이스(embed_documents,
    embed_query)를 기대하므로, chromadb 기본 함수를 그대로 못 넣고 감싸야 한다.
    """

    def __init__(self):
        self._fn = embedding_functions.DefaultEmbeddingFunction()

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [list(v) for v in self._fn(texts)]

    def embed_query(self, text: str) -> list[float]:
        return list(self._fn([text])[0])


def parse_metadata_from_filename(filename: str) -> dict:
    """파일명 '코드_제목_연도.pdf'에서 메타데이터 추출. 형식이 안 맞으면 파일명 전체를 제목으로."""
    stem = os.path.splitext(filename)[0]
    m = FILENAME_PATTERN.match(stem)
    if m:
        return {"code": m.group("code"), "title": m.group("title"), "year": int(m.group("year"))}
    return {"code": "UNKNOWN", "title": stem, "year": 0}


def build_vectorstore():
    pdf_paths = sorted(glob.glob(os.path.join(KOSHA_DIR, "*.pdf")))
    if not pdf_paths:
        print(f"{KOSHA_DIR} 안에 PDF가 없습니다. 먼저 KOSHA GUIDE PDF를 넣어주세요.")
        return

    all_docs = []
    for pdf_path in pdf_paths:
        filename = os.path.basename(pdf_path)
        meta = parse_metadata_from_filename(filename)
        print(f"로딩 중: {filename} (code={meta['code']}, year={meta['year']})")

        # PyPDFLoader.load()는 페이지별로 Document 객체를 만들어주고,
        # metadata에 자동으로 'source'(경로), 'page'(0-base 페이지번호)를 채워준다
        pages = PyPDFLoader(pdf_path).load()
        for doc in pages:
            doc.metadata.update({
                "source": filename,
                "code": meta["code"],
                "title": meta["title"],
                "year": meta["year"],
            })
        all_docs.extend(pages)

    if not all_docs:
        print("문서를 하나도 못 불러왔습니다.")
        return

    splitter = RecursiveCharacterTextSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)
    chunks = splitter.split_documents(all_docs)

    empty_chunks = sum(1 for c in chunks if not c.page_content.strip())
    if empty_chunks == len(chunks):
        print("텍스트를 추출하지 못했습니다 (스캔본 PDF일 수 있음 → OCR 필요).")
        return

    embeddings = ChromaDefaultEmbeddings()

    # 재실행 시 중복 누적 안 되게, 기존 컬렉션은 지우고 새로 만듦
    import chromadb as _chromadb
    _client = _chromadb.PersistentClient(path=PERSIST_DIR)
    try:
        _client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name=COLLECTION_NAME,
        persist_directory=PERSIST_DIR,
    )

    print(f"총 {len(chunks)}개 청크 저장 완료 → {PERSIST_DIR}/ (컬렉션: {COLLECTION_NAME})")


def query_guides(query: str, top_k: int = 3):
    """저장된 벡터DB에서 질의로 검색해보는 간단한 테스트 함수."""
    embeddings = ChromaDefaultEmbeddings()
    vectordb = Chroma(
        collection_name=COLLECTION_NAME,
        embedding_function=embeddings,
        persist_directory=PERSIST_DIR,
    )
    results = vectordb.similarity_search_with_score(query, k=top_k)

    for doc, score in results:
        meta = doc.metadata
        print(f"[{meta.get('code')} p.{meta.get('page')} / {meta.get('year')}년 / 거리={score:.3f}]")
        print(doc.page_content[:200].replace("\n", " "), "...\n")


if __name__ == "__main__":
    build_vectorstore()
