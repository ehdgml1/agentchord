# RAG 파이프라인 가이드

RAG(Retrieval-Augmented Generation)는 문서 검색과 LLM 생성을 결합해 AI 응답을 실제 문서 기반으로 만듭니다. AgentChord는 문서 로딩, 청킹, 임베딩, 벡터 검색, 하이브리드 검색, 리랭킹, 평가를 포함한 완전한 RAG 시스템을 제공합니다.

## 빠른 시작

OpenAI 임베딩을 사용한 기본 RAG 파이프라인:

```python
from agentchord.rag import RAGPipeline, OpenAIEmbeddings, TextLoader
from agentchord.llm.openai import OpenAIProvider

# RAG 파이프라인 설정
embeddings = OpenAIEmbeddings(api_key="your-key")
llm = OpenAIProvider(api_key="your-key", model="gpt-4o-mini")
pipeline = RAGPipeline(
    llm=llm,
    embedding_provider=embeddings
)

# 로더로 문서 수집
loaders = [
    TextLoader("doc1.txt"),
    TextLoader("doc2.txt"),
]
await pipeline.ingest(loaders)

# 컨텍스트와 함께 쿼리
result = await pipeline.query(
    question="AgentChord란 무엇인가요?",
    limit=3
)
print(result.answer)        # 검색된 문서를 컨텍스트로 사용한 응답
print(result.retrieval.contexts)  # 검색된 문서 목록
```

## 설치

RAG 의존성 설치:

```bash
# 기본 RAG (OpenAI 임베딩 + 인메모리 벡터 스토어)
pip install agentchord[rag]

# 전체 RAG (ChromaDB, FAISS, PDF/웹 로더, 리랭커 포함)
pip install agentchord[rag-full]
```

`[rag]` 추가 포함 항목:
- OpenAI 및 Ollama 임베딩
- 인메모리 벡터 스토어
- 텍스트 및 디렉토리 로더
- 기본 청킹 전략

`[rag-full]` 추가 항목:
- ChromaDB 및 FAISS 벡터 스토어
- PDF 로더 (pypdf)
- 웹 로더 (beautifulsoup4)
- SentenceTransformer 임베딩
- CrossEncoder 리랭킹

## 핵심 타입

```python
from agentchord.rag.types import Document, Chunk, SearchResult, RetrievalResult, RAGResponse

# Document: 청킹 전 소스 문서
doc = Document(
    content="Python은 프로그래밍 언어입니다",
    metadata={"source": "docs.txt"},
    source="docs.txt"
)

# Chunk: 분할 후 문서 조각
chunk = Chunk(
    content="Python은 고수준 프로그래밍 언어입니다",
    document_id="doc-123",
    metadata={"page": 1},
    embedding=[0.1, 0.2, ...]  # 임베딩 벡터
)

# RAGResponse: 완전한 RAG 응답
# result.answer        - LLM 생성 답변
# result.query         - 원본 쿼리
# result.retrieval     - RetrievalResult (검색 결과 + 타이밍)
# result.retrieval.contexts  - 검색된 컨텍스트 문자열 목록
```

## 문서 로더

다양한 소스에서 문서를 로드합니다.

### TextLoader

일반 텍스트 파일 로드:

```python
from agentchord.rag import TextLoader

loader = TextLoader(file_path="knowledge.txt")
documents = await loader.load()
# 반환: [Document(content="...", metadata={"source": "knowledge.txt"})]
```

### PDFLoader

PDF에서 텍스트 추출 (`[rag-full]` 필요):

```python
from agentchord.rag import PDFLoader

loader = PDFLoader(file_path="research.pdf")
documents = await loader.load()
# PDF 페이지당 하나의 Document
```

### WebLoader

웹 페이지 스크래핑 (`[rag-full]` 필요, beautifulsoup4 선택적):

```python
from agentchord.rag import WebLoader

loader = WebLoader(url="https://example.com/article")
documents = await loader.load()
# 반환: [Document(content="...", metadata={"source": "https://..."})]
```

beautifulsoup4가 없으면 정규식 기반 파서로 폴백합니다.

### DirectoryLoader

디렉토리에서 텍스트 파일 재귀적으로 로드:

```python
from agentchord.rag import DirectoryLoader

loader = DirectoryLoader(
    directory="./docs",
    file_pattern="*.md",
    recursive=True
)
documents = await loader.load()
# 파일당 하나의 Document
```

## 청킹 전략

문서를 임베딩과 검색에 적합한 작은 청크로 분할합니다.

### RecursiveCharacterChunker

오버랩이 있는 문자 기반 분할:

```python
from agentchord.rag import RecursiveCharacterChunker

chunker = RecursiveCharacterChunker(
    chunk_size=500,
    chunk_overlap=50
)
chunks = await chunker.chunk(document)
# 반환: [Chunk(...), Chunk(...), ...]
```

가능한 경우 자연스러운 경계 (단락, 문장)를 존중합니다.

여러 문서를 한번에 청킹:

```python
chunks = chunker.chunk_many(documents)
```

### SemanticChunker

의미적 유사성으로 청킹 (`[rag-full]` 필요):

```python
from agentchord.rag import SemanticChunker, OpenAIEmbeddings

embeddings = OpenAIEmbeddings(api_key="your-key")
chunker = SemanticChunker(
    embeddings=embeddings,
    similarity_threshold=0.5
)
chunks = await chunker.chunk(document)
# 유사도가 임계값 이하로 떨어지는 지점에서 분할
```

의미적 일관성에 따라 가변 길이 청크를 생성합니다.

### ParentChildChunker

검색용 소형 청크와 컨텍스트용 대형 청크 생성:

```python
from agentchord.rag import ParentChildChunker

chunker = ParentChildChunker(
    parent_chunk_size=1000,
    child_chunk_size=200,
    child_overlap=20
)
chunks = await chunker.chunk(document)
# 각 자식 청크는 메타데이터로 부모를 연결
```

소형 청크(정확)를 검색하지만 전체 부모 청크(풍부한 컨텍스트)를 반환합니다.

## 임베딩 프로바이더

텍스트를 벡터 임베딩으로 변환합니다.

### OpenAIEmbeddings

```python
from agentchord.rag import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(
    api_key="your-key",
    model="text-embedding-3-small",
    dimensions=1536
)

# 단일 텍스트 임베딩
vector = await embeddings.embed("Hello world")
# 반환: [0.123, -0.456, ..., 0.789]  (1536차원)

# 배치 임베딩 (최대 2048개 항목 자동 배치 처리)
vectors = await embeddings.embed_batch(["Doc 1", "Doc 2", "Doc 3"])
# 반환: [[...], [...], [...]]
```

### OllamaEmbeddings

로컬 Ollama 모델 사용:

```python
from agentchord.rag import OllamaEmbeddings

embeddings = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url="http://localhost:11434"
)

vector = await embeddings.embed("Hello world")
```

비동기 배치 처리 (`asyncio.gather` + Semaphore 10)로 동시 요청을 제한합니다.

### GeminiEmbeddings

Google Gemini 임베딩 API:

```python
from agentchord.rag.embeddings.gemini import GeminiEmbeddings

embeddings = GeminiEmbeddings(
    api_key="AIza...",
    model="text-embedding-004"  # 또는 "embedding-001"
)

vector = await embeddings.embed("Hello world")
# 배치는 100개 항목씩 자동 분할
```

### SentenceTransformerEmbeddings

로컬 SentenceTransformer 모델 (`[rag-full]` 필요):

```python
from agentchord.rag import SentenceTransformerEmbeddings

embeddings = SentenceTransformerEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

vector = await embeddings.embed("Hello world")
# 로컬 실행, API 키 불필요
```

## 벡터 스토어

임베딩을 저장하고 검색합니다.

### InMemoryVectorStore

빠른 인메모리 저장 (개발용):

```python
from agentchord.rag import InMemoryVectorStore, Chunk

vector_store = InMemoryVectorStore()

# 임베딩이 있는 청크 추가
chunks = [
    Chunk(content="Doc 1", embedding=[0.1, 0.2, ...]),
    Chunk(content="Doc 2", embedding=[0.3, 0.4, ...])
]
chunk_ids = await vector_store.add(chunks)

# 유사도로 검색
query_embedding = [0.15, 0.25, ...]
results = await vector_store.search(query_embedding, limit=5)
for result in results:
    print(f"{result.chunk.content} (score: {result.score})")

# 카운트
count = await vector_store.count()

# ID로 가져오기
chunk = await vector_store.get(chunk_ids[0])

# 전체 삭제
await vector_store.clear()
```

### ChromaVectorStore

영속성 벡터 데이터베이스 (`[rag-full]` 필요):

```python
from agentchord.rag import ChromaVectorStore, Chunk

vector_store = ChromaVectorStore(
    collection_name="knowledge_base",
    persist_directory="./chroma_db"
)

# 청크 추가
chunks = [Chunk(content="Doc", embedding=[0.1, ...])]
await vector_store.add(chunks)

# 임베딩으로 검색
query_embedding = [0.15, ...]
results = await vector_store.search(query_embedding, limit=5)

# ID로 가져오기
chunk = await vector_store.get(chunk_id)
```

### FAISSVectorStore

고성능 벡터 검색 (`[rag-full]` 필요):

```python
from agentchord.rag import FAISSVectorStore, Chunk

vector_store = FAISSVectorStore(
    dimensions=1536,
    index_type="flat"  # "flat" 또는 "ivf" (approximate)
)

# 청크 추가
chunks = [Chunk(content="Doc", embedding=[0.1, ...] * 1536)]
await vector_store.add(chunks)

# 검색
query_embedding = [0.15, ...] * 1536
results = await vector_store.search(query_embedding, limit=5)
```

## 검색 전략

### BM25Search

순수 Python 키워드 검색 (Okapi BM25 알고리즘):

```python
from agentchord.rag import BM25Search

# 청크로 인덱싱
search = BM25Search(k1=1.5, b=0.75)
search.index(chunks)

# 검색 (동기 메서드)
results = search.search("쿼리", limit=5)
for result in results:
    print(f"{result.chunk.content} (score: {result.score})")
```

BM25는 키워드 매칭에 적합하며 임베딩이 필요 없습니다.

### HybridSearch

Reciprocal Rank Fusion으로 의미 검색(벡터)과 키워드 검색(BM25)을 결합:

```python
from agentchord.rag import HybridSearch, InMemoryVectorStore, OpenAIEmbeddings, BM25Search

embeddings = OpenAIEmbeddings(api_key="your-key")
vector_store = InMemoryVectorStore()
bm25 = BM25Search()

search = HybridSearch(
    vectorstore=vector_store,
    embedding_provider=embeddings,
    bm25=bm25,
    rrf_k=60  # RRF 파라미터
)

# 청크 추가 (필요 시 자동 임베딩)
chunks = [Chunk(content="Doc 1"), Chunk(content="Doc 2")]
await search.add(chunks)

# 벡터 유사도와 BM25 키워드 매칭 결합
result = await search.search("쿼리", limit=5)
print(result.results)  # 타이밍 메트릭이 있는 RetrievalResult
```

하이브리드 검색은 의미 전용이나 키워드 전용보다 자주 더 나은 성능을 보입니다.

## 리랭킹

검색된 결과의 관련성을 개선하기 위해 리랭킹합니다.

### CrossEncoderReranker

크로스 인코더 모델 사용 (`[rag-full]` 필요):

```python
from agentchord.rag import CrossEncoderReranker

reranker = CrossEncoderReranker(
    model_name="cross-encoder/ms-marco-MiniLM-L-6-v2"
)

# 검색 결과 리랭킹
reranked = await reranker.rerank(
    query="Python이란 무엇인가요?",
    results=search_results,
    top_n=3
)
```

크로스 인코더는 더 정확한 관련성 점수를 제공하지만 더 느립니다.

### LLMReranker

LLM으로 결과 리랭킹:

```python
from agentchord.rag import LLMReranker
from agentchord.llm.openai import OpenAIProvider

llm = OpenAIProvider(api_key="your-key", model="gpt-4o-mini")
reranker = LLMReranker(llm_provider=llm)

reranked = await reranker.rerank(
    query="Python이란 무엇인가요?",
    results=search_results,
    top_n=3
)
```

## RAGPipeline

완전한 엔드-투-엔드 RAG 워크플로우.

### 기본 파이프라인

```python
from agentchord.rag import RAGPipeline, OpenAIEmbeddings, TextLoader
from agentchord.llm.openai import OpenAIProvider

embeddings = OpenAIEmbeddings(api_key="your-key")
llm = OpenAIProvider(api_key="your-key", model="gpt-4o-mini")

pipeline = RAGPipeline(
    llm=llm,
    embedding_provider=embeddings
    # 기본값: InMemoryVectorStore, RecursiveCharacterChunker, BM25 활성화
)

# 로더로 문서 수집
loaders = [TextLoader("doc1.txt"), TextLoader("doc2.txt")]
await pipeline.ingest(loaders)

# 쿼리
result = await pipeline.query(
    question="답이 무엇인가요?",
    limit=5
)
print(result.answer)
print(result.retrieval.contexts)  # 검색된 문서들
```

### 고급 파이프라인

청킹, 하이브리드 검색, 리랭킹 포함:

```python
from agentchord.rag import (
    RAGPipeline, OpenAIEmbeddings, InMemoryVectorStore,
    RecursiveCharacterChunker, CrossEncoderReranker, TextLoader
)
from agentchord.llm.openai import OpenAIProvider

# 컴포넌트 설정
embeddings = OpenAIEmbeddings(api_key="your-key")
llm = OpenAIProvider(api_key="your-key", model="gpt-4o")
vector_store = InMemoryVectorStore()
chunker = RecursiveCharacterChunker(chunk_size=500, chunk_overlap=50)
reranker = CrossEncoderReranker()

# 파이프라인 생성
pipeline = RAGPipeline(
    llm=llm,
    embedding_provider=embeddings,
    vectorstore=vector_store,
    chunker=chunker,
    reranker=reranker,
    enable_bm25=True,     # 내부적으로 하이브리드 검색 활성화
    search_limit=5,       # 컨텍스트로 사용할 검색 결과 수
)

# 문서 로드 및 수집
loader = TextLoader("knowledge.txt")
documents = await loader.load()
await pipeline.ingest_documents(documents)

# 리랭킹을 포함한 쿼리
result = await pipeline.query(question="질문", limit=10)
```

### 파이프라인 파라미터

| 파라미터 | 기본값 | 설명 |
|---------|--------|------|
| `llm` | 필수 | 답변 생성용 LLM 프로바이더 |
| `embedding_provider` | 필수 | 벡터화용 임베딩 프로바이더 |
| `vectorstore` | InMemoryVectorStore | 벡터 스토어 백엔드 |
| `chunker` | RecursiveCharacterChunker | 문서 청커 |
| `reranker` | None | 선택적 리랭커 |
| `system_prompt` | 기본 RAG 프롬프트 | `{context}` 플레이스홀더 사용 |
| `search_limit` | 5 | 컨텍스트로 사용할 검색 결과 수 |
| `enable_bm25` | True | 하이브리드 BM25 검색 활성화 |

### 단계별 실행

각 단계를 개별적으로 실행할 수 있습니다:

```python
# 1. 수집
await pipeline.ingest(loaders)
print(f"수집된 청크: {pipeline.ingested_count}")

# 2. 검색
retrieval = await pipeline.retrieve(
    query="질문",
    limit=5,
    filter={"source": "manual"}  # 선택적 메타데이터 필터
)

# 3. 생성
response = await pipeline.generate(
    query="질문",
    retrieval=retrieval,
    temperature=0.3,
    max_tokens=1024
)
print(response.answer)
```

### 라이프사이클 관리

비동기 컨텍스트 관리자 사용:

```python
async with RAGPipeline(llm=llm, embedding_provider=embeddings) as pipeline:
    await pipeline.ingest(loaders)
    result = await pipeline.query(question="질문")
# 파이프라인 리소스 자동 정리
```

또는 수동 관리:

```python
pipeline = RAGPipeline(llm=llm, embedding_provider=embeddings)
try:
    await pipeline.ingest(loaders)
    result = await pipeline.query(question="질문")
finally:
    await pipeline.close()
```

## Agentic RAG

에이전트 도구 호출 워크플로우를 위한 RAG 도구 생성:

```python
from agentchord.rag import create_rag_tools, RAGPipeline, OpenAIEmbeddings, TextLoader
from agentchord.llm.openai import OpenAIProvider
from agentchord import Agent

# RAG 파이프라인 설정
embeddings = OpenAIEmbeddings(api_key="your-key")
llm = OpenAIProvider(api_key="your-key", model="gpt-4o-mini")
pipeline = RAGPipeline(llm=llm, embedding_provider=embeddings)

# 문서 수집
loaders = [TextLoader("doc1.txt"), TextLoader("doc2.txt")]
await pipeline.ingest(loaders)

# 도구 생성
tools = create_rag_tools(pipeline=pipeline, search_limit=5)
# 반환: [rag_search, rag_query]

# RAG 도구를 가진 에이전트
agent = Agent(
    name="assistant",
    role="지식 베이스를 가진 도움이 되는 어시스턴트",
    llm_provider=llm,
    tools=tools
)

# 에이전트가 필요할 때 rag_search() 또는 rag_query() 호출
result = await agent.run("AgentChord란 무엇인가요?")
```

에이전트가 언제 지식 베이스를 검색할지 결정합니다.

## 평가

RAGAS 스타일 메트릭으로 RAG 파이프라인 품질을 평가합니다.

```python
from agentchord.rag.evaluation.evaluator import RAGEvaluator
from agentchord.llm.openai import OpenAIProvider

llm = OpenAIProvider(api_key="your-key", model="gpt-4o-mini")
evaluator = RAGEvaluator(llm=llm)

# 단일 응답 평가
result = await evaluator.evaluate(
    query="Python이란 무엇인가요?",
    answer="Python은 고수준 프로그래밍 언어입니다.",
    contexts=["Python은 1991년에 만들어진 프로그래밍 언어입니다."]
)

print(f"RAGAS 점수: {result.ragas_score}")  # 조화 평균
for metric in result.metrics:
    print(f"{metric.name}: {metric.score}")
# Faithfulness, Answer Relevancy, Context Relevancy

# 또는 RAGResponse를 직접 평가
response = await pipeline.query(question="Python이란 무엇인가요?")
result = await evaluator.evaluate_response(response)
```

**평가 메트릭** (0.0-1.0, 높을수록 좋음):
- **Faithfulness**: 답변이 컨텍스트에 충실한지
- **Answer Relevancy**: 답변이 질문과 관련 있는지
- **Context Relevancy**: 검색된 컨텍스트가 관련 있는지
- **RAGAS Score**: 세 메트릭의 조화 평균

평가는 병렬로 실행됩니다 (`asyncio.gather`).

## 베스트 프랙티스

### 1. 적절한 청크 크기 선택

```python
# 정확한 검색용 (Q&A)
chunker = RecursiveCharacterChunker(chunk_size=300, chunk_overlap=30)

# 컨텍스트 풍부한 검색용 (요약)
chunker = RecursiveCharacterChunker(chunk_size=1000, chunk_overlap=100)
```

### 2. 프로덕션에서 하이브리드 검색 사용

```python
# BM25를 파이프라인에서 활성화 (기본값)
pipeline = RAGPipeline(
    llm=llm,
    embedding_provider=embeddings,
    enable_bm25=True  # 기본값 True
)
```

### 3. 더 많이 검색하고 리랭킹

```python
# 20개 검색 후 상위 5개로 리랭킹
retrieval = await pipeline.retrieve(query, limit=20)
reranked = await reranker.rerank(query, retrieval.results, top_n=5)
```

### 4. 필터링을 위한 메타데이터 추가

```python
chunks = [
    Chunk(
        content="Doc 1",
        metadata={"source": "manual", "version": "1.0"},
        embedding=[...]
    ),
]
await vector_store.add(chunks)

# 메타데이터로 필터링
results = await vector_store.search(
    query_embedding,
    limit=5,
    filter={"source": "manual"}
)
```

### 5. 검색된 컨텍스트 품질 모니터링

```python
result = await pipeline.query(question="질문")
for i, ctx in enumerate(result.retrieval.contexts):
    print(f"컨텍스트 {i+1}: {ctx[:100]}...")
# 검색된 내용 검사
```

## 완전한 예제

```python
import asyncio
from agentchord.rag import (
    RAGPipeline,
    OpenAIEmbeddings,
    RecursiveCharacterChunker,
    TextLoader,
)
from agentchord.rag.evaluation.evaluator import RAGEvaluator
from agentchord.llm.openai import OpenAIProvider


async def main():
    # 컴포넌트 초기화
    api_key = "your-openai-key"
    embeddings = OpenAIEmbeddings(api_key=api_key)
    llm = OpenAIProvider(api_key=api_key, model="gpt-4o-mini")

    # 파이프라인 생성
    pipeline = RAGPipeline(
        llm=llm,
        embedding_provider=embeddings,
        chunker=RecursiveCharacterChunker(chunk_size=400, chunk_overlap=40),
        enable_bm25=True,
        search_limit=5,
    )

    # 문서 수집
    async with pipeline:
        loaders = [TextLoader("knowledge.txt")]
        count = await pipeline.ingest(loaders)
        print(f"수집된 청크: {count}")

        # 쿼리
        questions = [
            "AgentChord란 무엇인가요?",
            "어떻게 에이전트를 만드나요?",
        ]

        for question in questions:
            result = await pipeline.query(question=question)
            print(f"\n질문: {question}")
            print(f"답변: {result.answer[:200]}...")
            print(f"검색된 컨텍스트 수: {len(result.retrieval.results)}")

        # 파이프라인 평가
        evaluator = RAGEvaluator(llm=llm)
        eval_result = await evaluator.evaluate(
            query="AgentChord란 무엇인가요?",
            answer=result.answer,
            contexts=result.retrieval.contexts
        )
        print(f"\n평가 점수: {eval_result.ragas_score:.3f}")


if __name__ == "__main__":
    asyncio.run(main())
```

## 참고

- [도구 가이드](tools.md) - Agentic 도구 호출과 RAG 사용
- [메모리 가이드](memory.md) - 대화 메모리 vs RAG
- [Agent API](../api/core.md) - Agent API 상세 정보
- [예제](../examples.md) - RAG 전체 예제
