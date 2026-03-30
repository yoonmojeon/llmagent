"""
RAG MCP Server
ChromaDB + OpenAI text-embedding-3-small 기반 해양 도메인 지식 검색 서버

지식 소스:
  - osp-is-1.0.1.pdf           : OSP Interface Specification (79p)
  - fmi-standard-2.0.pdf       : FMI 2.0 표준 (126p)
  - 01_osp_overview.txt        : OSP 개요
  - 02_osp_cosimulation.txt    : OSP Co-simulation
  - 03_osp_use_cases_crane.txt : 크레인 적용 사례
  - 04_wikipedia_dynamic_positioning.txt : 동적 위치 유지(DP)
  - 05_wikipedia_crane_vessel.txt        : 크레인 선박
  - 06_wikipedia_power_outage_marine.txt : 해양 전력 차단
  - 07_mcp_llm_agent_framework.txt       : LLM 에이전트 프레임워크
  - 08_wikipedia_offshore_construction.txt : 해양 건설
  - 09_construction_vessel_variables.txt   : 건설 선박 변수
"""

import asyncio
import os
from pathlib import Path

import mcp.types as types
from mcp.server import Server
from mcp.server.stdio import stdio_server
from dotenv import load_dotenv

BASE_DIR        = Path(__file__).parent
CHROMA_DIR      = str(BASE_DIR / "rag" / "chroma_db")
COLLECTION_NAME = "maritime_knowledge"
EMBED_MODEL     = "text-embedding-3-small"

load_dotenv(BASE_DIR / ".env")

app = Server("rag-mcp-server")

# 컬렉션은 첫 호출 시 한 번만 초기화
_collection = None


def _get_collection():
    global _collection
    if _collection is not None:
        return _collection

    import chromadb
    from chromadb.utils.embedding_functions import OpenAIEmbeddingFunction

    if not os.path.exists(CHROMA_DIR):
        raise RuntimeError(
            f"ChromaDB를 찾을 수 없습니다: {CHROMA_DIR}\n"
            "rag/build_vectordb.py 를 먼저 실행하세요."
        )

    api_key  = os.getenv("OPENAI_API_KEY")
    embed_fn = OpenAIEmbeddingFunction(api_key=api_key, model_name=EMBED_MODEL)
    client   = chromadb.PersistentClient(path=CHROMA_DIR)
    _collection = client.get_collection(COLLECTION_NAME, embedding_function=embed_fn)
    return _collection


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="rag_search",
            description=(
                "해양 도메인 지식베이스에서 의미 유사도 기반으로 관련 문서를 검색합니다.\n"
                "OSP Interface Specification, FMI 2.0 표준, 동적 위치 유지(DP), "
                "크레인 선박, 해양 전력 관리, 해양 건설 등에 관한 질문에 답변할 수 있습니다."
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "검색할 질문 또는 키워드 (한국어/영어 모두 가능)"
                    },
                    "top_k": {
                        "type": "integer",
                        "description": "반환할 최대 문서 청크 수 (기본값: 4, 최대: 10)"
                    }
                },
                "required": ["query"]
            }
        ),
        types.Tool(
            name="rag_info",
            description="현재 로드된 해양 지식베이스의 정보를 반환합니다 (문서 수, 소스 목록 등).",
            inputSchema={
                "type": "object",
                "properties": {}
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    try:
        if name == "rag_search":
            return await _rag_search(arguments)
        elif name == "rag_info":
            return await _rag_info(arguments)
        else:
            return [types.TextContent(type="text", text=f"알 수 없는 도구: {name}")]
    except Exception as e:
        return [types.TextContent(type="text", text=f"RAG 오류 [{name}]: {str(e)}")]


async def _rag_search(args: dict) -> list[types.TextContent]:
    query = args["query"]
    top_k = min(int(args.get("top_k", 4)), 10)

    col = _get_collection()
    n   = min(top_k, col.count())

    if n == 0:
        return [types.TextContent(type="text", text="지식베이스가 비어 있습니다.")]

    results = col.query(query_texts=[query], n_results=n)

    parts = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        sim    = max(0.0, 1.0 - dist)
        source = meta.get("source", "unknown")
        page   = meta.get("page", "")
        loc    = f"{source}" + (f" p.{page}" if page else "")
        parts.append(f"[{loc}] (유사도: {sim:.3f})\n{doc.strip()}")

    joined = "\n\n---\n\n".join(parts)
    header = f"검색어: \"{query}\"  |  결과 {len(parts)}건\n\n"
    return [types.TextContent(type="text", text=header + joined)]


async def _rag_info(args: dict) -> list[types.TextContent]:
    col   = _get_collection()
    count = col.count()

    # 소스 파일 목록
    docs_dir = BASE_DIR / "rag" / "docs"
    sources  = []
    if docs_dir.exists():
        for f in sorted(docs_dir.iterdir()):
            size = f.stat().st_size
            size_str = f"{size / 1024:.0f} KB" if size >= 1024 else f"{size} B"
            sources.append(f"  - {f.name}  ({size_str})")

    lines = [
        f"지식베이스: {COLLECTION_NAME}",
        f"임베딩 모델: {EMBED_MODEL}",
        f"저장 경로: {CHROMA_DIR}",
        f"총 청크 수: {count:,}개",
        "",
        "문서 소스:",
    ] + sources

    return [types.TextContent(type="text", text="\n".join(lines))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())
