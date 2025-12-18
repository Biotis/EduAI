from typing import Dict, Any, List
from llama_index.core import Document  # 최신 버전 기준; 안 되면 legacy에서 import 필요
from llama_index.core.chat_engine import ContextChatEngine

_CHAT_ENGINES: Dict[str, ContextChatEngine] = {}

def build_documents_from_docai(doc: Dict[str, Any], doc_id: str, filename: str) -> List[Document]:
    documents: List[Document] = []

    for page in doc.get("pages", []):
        text = (page.get("text") or "").strip()
        if not text:
            continue

        page_idx = page.get("index", None)

        documents.append(
            Document(
                text=text,
                metadata={
                    "doc_id": doc_id,
                    "filename": filename,
                    "page": page_idx,
                },
            )
        )

    return documents

import lancedb
from llama_index.core import VectorStoreIndex, Settings, StorageContext
from llama_index.vector_stores.lancedb import LanceDBVectorStore  # 공식 예시와 동일 계열 :contentReference[oaicite:5]{index=5}
import os
from typing import Dict, Any, List
from llama_index.core import VectorStoreIndex, Settings, StorageContext
from llama_index.vector_stores.lancedb import LanceDBVectorStore
from llama_index.llms.google_genai import GoogleGenAI
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding  # 또는 버전에 따라 GeminiEmbedding

def _init_llama_settings() -> None:
    """Vertex 기반 LLM/임베딩 공통 세팅."""
    vertexai_config = {
        "project": os.getenv("GOOGLE_CLOUD_PROJECT"),
        "location": "us-central1",
    }

    Settings.llm = GoogleGenAI(
        model="gemini-2.5-flash",
        vertexai_config=vertexai_config,
    )

    Settings.embed_model = GoogleGenAIEmbedding(
        model_name="text-embedding-005",
        vertexai_config=vertexai_config,
    )

    # 페이지 단위로 chunk 유지하고 싶으면 넉넉히
    Settings.chunk_size = 8000

def build_index_with_lancedb(doc: Dict[str, Any], doc_id: str, filename: str):
    documents = build_documents_from_docai(doc, doc_id, filename)

    _init_llama_settings()

    table = f'lectures_{doc_id}'
    # table = f'lectures'
    vector_store = LanceDBVectorStore(
        uri="./lancedb",
        table_name=table,  # 원하는 이름
        # mode="overwrite"  
    )

    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        show_progress=True,
    )

    return index, vector_store

def load_index_from_lancedb(doc_id) -> VectorStoreIndex:
    _init_llama_settings()

    vector_store = LanceDBVectorStore(
        uri="./lancedb",
        table_name=f'lectures_{doc_id}',
    )
    storage_context = StorageContext.from_defaults(vector_store=vector_store)

    index = VectorStoreIndex.from_vector_store(
        vector_store=vector_store,
        storage_context=storage_context,
    )
    return index

from llama_index.core.vector_stores import ExactMatchFilter, MetadataFilters

def _get_chat_engine_for_doc(doc_id: str) -> ContextChatEngine:
    """doc_id 단위로 ChatEngine을 생성/재사용 (히스토리 포함)."""
    if doc_id in _CHAT_ENGINES:
        return _CHAT_ENGINES[doc_id]

    index = load_index_from_lancedb(doc_id)
    print('index 연결 성공')
    # 이 문서(doc_id)에 해당하는 페이지만 retrieval 대상이 되도록 메타 필터
    # filters = MetadataFilters(
    #     filters=[
    #         ExactMatchFilter(key="doc_id", value=doc_id),
    #     ]
    # )

    retriever = index.as_retriever(
        similarity_top_k=5,
        # filters=filters,
    )

    print('retriever ok')

    chat_engine = ContextChatEngine.from_defaults(
        retriever=retriever,
        llm=Settings.llm,
        chat_history=[],  # 새 대화
    )

    print(chat_engine)

    _CHAT_ENGINES[doc_id] = chat_engine
    return chat_engine

def chat_with_rag(doc_id: str, message: str) -> Dict[str, Any]:
    """
    하나의 문서(doc_id)를 대상으로 RAG + 대화 히스토리 기반 응답 생성.
    """
    chat_engine = _get_chat_engine_for_doc(doc_id)

    resp = chat_engine.chat(message)

    # resp는 Response 객체
    answer_text = str(resp)

    # 원하면 근거로 사용된 페이지 정보도 같이 반환
    sources = []
    for node in getattr(resp, "source_nodes", []) or []:
        meta = node.node.metadata or {}
        sources.append(
            {
                "page": meta.get("page"),
                "doc_id": meta.get("doc_id"),
                "score": float(node.score) if node.score is not None else None,
            }
        )

    return {
        "answer": answer_text,
        "sources": sources,
    }

# def rag_query(doc_id: str, question: str, top_k: int = 5) -> str:
#     """
#     하나의 doc_id에 대해서만 RAG 검색 + 답변 생성.
#     """
#     index = load_index_from_lancedb()

#     # doc_id로 필터링
#     filters = MetadataFilters(
#         filters=[
#             ExactMatchFilter(key="doc_id", value=doc_id),
#         ]
#     )

#     query_engine = index.as_query_engine(
#         similarity_top_k=top_k,
#         filters=filters,
#     )

#     response = query_engine.query(question)
#     # response는 Response 객체이므로 str()로 텍스트만 뽑아 사용
#     return str(response)

