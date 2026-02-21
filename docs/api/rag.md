# RAG API 레퍼런스

AgentChord RAG (Retrieval-Augmented Generation) 시스템에 대한 완전한 API 레퍼런스입니다. 문서 로딩, 청킹, 임베딩, 벡터 저장소, 검색, 평가를 다룹니다.

---

## 타입

### Document

청킹 이전의 원본 문서를 나타내는 Pydantic 모델입니다.

```python
from agentchord.rag.types import Document

doc = Document(
    content="AgentChord는 멀티 에이전트 프레임워크입니다.",
    source="docs/readme.md",
    metadata={"author": "team", "version": "1.0"},
)

print(doc.id)         # 자동 생성 UUID
print(doc.created_at) # 생성 시각 (UTC)
```

**필드:**

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `id` | `str` | 자동 UUID | 문서 고유 ID |
| `content` | `str` | 필수 | 문서 내용 |
| `metadata` | `dict[str, Any]` | `{}` | 추가 메타데이터 |
| `source` | `str` | `""` | 소스 경로 또는 URL |
| `created_at` | `datetime` | 현재 UTC | 문서 생성 시각 |

---

### Chunk

청킹 후 생성된 문서 조각을 나타내는 Pydantic 모델입니다.

**필드:**

| 필드 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `id` | `str` | 자동 UUID | 청크 고유 ID |
| `content` | `str` | 필수 | 청크 내용 |
| `document_id` | `str` | `""` | 원본 문서 ID |
| `metadata` | `dict[str, Any]` | `{}` | 메타데이터 (원본 문서에서 상속) |
| `start_index` | `int` | `0` | 원본 문서 내 시작 위치 |
| `end_index` | `int` | `0` | 원본 문서 내 종료 위치 |
| `embedding` | `list[float] \| None` | `None` | 벡터 임베딩 |
| `parent_id` | `str \| None` | `None` | 부모 청크 ID (ParentChild 청킹용) |

---

### SearchResult

점수가 포함된 단일 검색 결과 Pydantic 모델입니다.

**필드:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `chunk` | `Chunk` | 검색된 청크 |
| `score` | `float` | 관련성 점수 |
| `source` | `str` | 검색 소스 (`"vector"`, `"bm25"`, `"hybrid"`) |

---

### RetrievalResult

RAG 쿼리의 전체 검색 결과 Pydantic 모델입니다.

```python
result = await pipeline.retrieve("AgentChord란?")

print(result.query)        # 원래 쿼리
print(result.contexts)     # 컨텍스트 문자열 목록
print(result.context_string)  # 구분자로 합산된 컨텍스트
print(result.retrieval_ms) # 검색 소요 시간 (ms)
```

**필드:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `query` | `str` | 원래 검색 쿼리 |
| `results` | `list[SearchResult]` | 검색 결과 목록 |
| `metadata` | `dict[str, Any]` | 추가 메타데이터 |
| `retrieval_ms` | `float` | 검색 소요 시간 (ms) |
| `rerank_ms` | `float` | 리랭킹 소요 시간 (ms) |
| `total_ms` | `float` | 전체 소요 시간 (ms) |

**프로퍼티:**

| 프로퍼티 | 타입 | 설명 |
|----------|------|------|
| `contexts` | `list[str]` | LLM 프롬프트용 컨텍스트 문자열 목록 |
| `context_string` | `str` | `"\n\n---\n\n"` 구분자로 합산된 컨텍스트 |

---

### RAGResponse

검색 및 생성을 포함한 전체 RAG 응답 Pydantic 모델입니다.

```python
response = await pipeline.query("AgentChord란?")

print(response.answer)           # LLM이 생성한 답변
print(response.query)            # 원래 질문
print(response.usage)            # 토큰 사용량
print(response.source_documents) # 참조된 문서 ID 목록
```

**필드:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `query` | `str` | 원래 질문 |
| `answer` | `str` | LLM이 생성한 답변 |
| `retrieval` | `RetrievalResult` | 검색 결과 |
| `usage` | `dict[str, int]` | 토큰 사용량 (`prompt_tokens`, `completion_tokens`, `total_tokens`) |
| `source_documents` | `list[str]` | 참조된 원본 문서 ID 목록 |

---

## RAGPipeline

전체 RAG 워크플로우(수집 → 검색 → 생성)를 조율하는 파이프라인입니다.

```python
from agentchord.rag import RAGPipeline
from agentchord.rag.loaders.text import TextLoader
from agentchord.rag.embeddings.openai import OpenAIEmbeddings
from agentchord.llm.openai import OpenAIProvider

pipeline = RAGPipeline(
    llm=OpenAIProvider(model="gpt-4o-mini"),
    embedding_provider=OpenAIEmbeddings(),
    search_limit=5,
    enable_bm25=True,
)

# 문서 수집
count = await pipeline.ingest([TextLoader("docs/readme.txt")])
print(f"{count}개 청크 수집 완료")

# 질의
response = await pipeline.query("AgentChord란 무엇인가요?")
print(response.answer)
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `llm` | `BaseLLMProvider` | 필수 | 답변 생성용 LLM 프로바이더 |
| `embedding_provider` | `EmbeddingProvider` | 필수 | 벡터화용 임베딩 프로바이더 |
| `vectorstore` | `VectorStore \| None` | `None` | 벡터 저장소. None이면 `InMemoryVectorStore` 사용 |
| `chunker` | `Chunker \| None` | `None` | 문서 청커. None이면 `RecursiveCharacterChunker` 사용 |
| `reranker` | `Reranker \| None` | `None` | 2단계 리랭커 (선택 사항) |
| `system_prompt` | `str` | 기본 프롬프트 | 시스템 프롬프트 템플릿. `{context}` 플레이스홀더 사용 |
| `search_limit` | `int` | `5` | 컨텍스트로 사용할 검색 결과 수 |
| `enable_bm25` | `bool` | `True` | BM25를 활용한 하이브리드 검색 사용 여부 |

**프로퍼티:**

| 프로퍼티 | 타입 | 설명 |
|----------|------|------|
| `ingested_count` | `int` | 수집된 청크 수 |

**메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `ingest` | `async ingest(loaders: list[DocumentLoader]) -> int` | `int` | 로더에서 문서 수집. 파이프라인: 로드→청킹→임베딩→저장 |
| `ingest_documents` | `async ingest_documents(documents: list[Document]) -> int` | `int` | 이미 로드된 문서 직접 수집 |
| `retrieve` | `async retrieve(query: str, limit: int \| None = None, *, filter: dict \| None = None) -> RetrievalResult` | `RetrievalResult` | 쿼리에 관련된 컨텍스트 검색 |
| `generate` | `async generate(query: str, retrieval: RetrievalResult, *, temperature: float = 0.3, max_tokens: int = 1024) -> RAGResponse` | `RAGResponse` | 검색된 컨텍스트로 답변 생성 |
| `query` | `async query(question: str, *, limit: int \| None = None, filter: dict \| None = None, temperature: float = 0.3, max_tokens: int = 1024) -> RAGResponse` | `RAGResponse` | 검색+생성 통합 메서드 |
| `clear` | `async clear() -> None` | `None` | 수집된 데이터 전체 삭제 |
| `close` | `async close() -> None` | `None` | 파이프라인 리소스 해제 (멱등성 보장) |

**비동기 컨텍스트 매니저 지원:**

```python
async with RAGPipeline(llm=..., embedding_provider=...) as pipeline:
    await pipeline.ingest([TextLoader("docs/")])
    response = await pipeline.query("질문")
# 자동으로 pipeline.close() 호출
```

---

## 문서 로더

### DocumentLoader (추상 기본 클래스)

모든 문서 로더가 구현해야 하는 추상 인터페이스입니다.

```python
from agentchord.rag.loaders.base import DocumentLoader
from agentchord.rag.types import Document

class MyLoader(DocumentLoader):
    async def load(self) -> list[Document]:
        # 커스텀 로딩 로직
        return [Document(content="...", source="custom")]
```

**추상 메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `load` | `async load() -> list[Document]` | `list[Document]` | 소스에서 문서 로드 |

---

### TextLoader

단일 텍스트 파일을 Document로 로드합니다.

```python
from agentchord.rag.loaders.text import TextLoader

loader = TextLoader("data/readme.txt", encoding="utf-8")
docs = await loader.load()
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `file_path` | `str \| Path` | 필수 | 텍스트 파일 경로 |
| `encoding` | `str` | `"utf-8"` | 파일 인코딩 |

---

### DirectoryLoader

디렉토리 내 텍스트 파일들을 재귀적으로 로드합니다.

```python
from agentchord.rag.loaders.directory import DirectoryLoader

loader = DirectoryLoader("docs/", glob="**/*.md")
docs = await loader.load()
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `directory` | `str \| Path` | 필수 | 로딩할 디렉토리 경로 |
| `glob` | `str` | `"**/*.txt"` | 파일 검색 패턴 |
| `encoding` | `str` | `"utf-8"` | 파일 인코딩 |

---

### WebLoader

URL에서 웹 페이지를 로드합니다.

```python
from agentchord.rag.loaders.web import WebLoader

loader = WebLoader("https://docs.agentchord.dev/")
docs = await loader.load()
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `url` | `str` | 필수 | 로드할 URL |
| `timeout` | `float` | `30.0` | HTTP 요청 타임아웃 (초) |

> `beautifulsoup4` 설치 시 HTML 파싱 품질이 향상됩니다. 없으면 정규식 기반 폴백 사용.

---

### PDFLoader

PDF 파일에서 텍스트를 로드합니다.

```python
from agentchord.rag.loaders.pdf import PDFLoader

loader = PDFLoader("docs/report.pdf")
docs = await loader.load()
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `file_path` | `str \| Path` | 필수 | PDF 파일 경로 |

> `pypdf` 패키지 필요: `pip install agentchord[rag]`

---

## 청커

### Chunker (추상 기본 클래스)

모든 청킹 전략이 구현해야 하는 추상 인터페이스입니다.

**추상 메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `chunk` | `chunk(document: Document) -> list[Chunk]` | `list[Chunk]` | 문서를 청크로 분할 |
| `chunk_many` | `chunk_many(documents: list[Document]) -> list[Chunk]` | `list[Chunk]` | 다수 문서 일괄 청킹 |

---

### RecursiveCharacterChunker

계층적 구분자를 사용해 텍스트를 재귀적으로 분할합니다. 범용 텍스트 청킹의 표준입니다.

```python
from agentchord.rag.chunking.recursive import RecursiveCharacterChunker

chunker = RecursiveCharacterChunker(
    chunk_size=500,     # 청크 최대 길이
    chunk_overlap=50,   # 청크 간 오버랩
)
chunks = chunker.chunk(document)
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `chunk_size` | `int` | `500` | 청크 최대 문자 길이 |
| `chunk_overlap` | `int` | `50` | 인접 청크 간 오버랩 문자 수 |
| `separators` | `list[str] \| None` | `["\n\n", "\n", ". ", " ", ""]` | 분할 구분자 목록 (우선순위 순) |
| `length_function` | `Callable[[str], int]` | `len` | 길이 계산 함수 |

> 분할 시도 순서: 단락(`\n\n`) → 줄바꿈(`\n`) → 문장(`. `) → 단어(` `) → 문자(`""`)

---

## 임베딩 프로바이더

### EmbeddingProvider (추상 기본 클래스)

모든 임베딩 프로바이더가 구현해야 하는 추상 인터페이스입니다.

```python
from agentchord.rag.embeddings.base import EmbeddingProvider

class MyEmbeddings(EmbeddingProvider):
    @property
    def model_name(self) -> str:
        return "my-model"

    @property
    def dimensions(self) -> int:
        return 768

    async def embed(self, text: str) -> list[float]:
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        ...
```

**추상 프로퍼티:**

| 프로퍼티 | 타입 | 설명 |
|----------|------|------|
| `model_name` | `str` | 임베딩 모델 이름 |
| `dimensions` | `int` | 임베딩 벡터 차원 수 |

**추상 메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `embed` | `async embed(text: str) -> list[float]` | `list[float]` | 단일 텍스트 임베딩 |
| `embed_batch` | `async embed_batch(texts: list[str]) -> list[list[float]]` | `list[list[float]]` | 다수 텍스트 배치 임베딩 |

---

### OpenAIEmbeddings

OpenAI 임베딩 API를 사용합니다.

```python
from agentchord.rag.embeddings.openai import OpenAIEmbeddings

embedder = OpenAIEmbeddings(
    model="text-embedding-3-small",
    api_key="sk-...",  # None이면 OPENAI_API_KEY 환경 변수 사용
)
vector = await embedder.embed("텍스트")
```

**지원 모델:**

| 모델 | 차원 | 설명 |
|------|------|------|
| `text-embedding-3-small` | 1536 | 가성비 모델 (기본값) |
| `text-embedding-3-large` | 3072 | 고성능 모델 |
| `text-embedding-ada-002` | 1536 | 레거시 모델 |

---

### OllamaEmbeddings

로컬 Ollama 서버를 사용한 임베딩입니다.

```python
from agentchord.rag.embeddings.ollama import OllamaEmbeddings

embedder = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url="http://localhost:11434",
)
```

---

### GeminiEmbeddings

Google Gemini 임베딩 API를 사용합니다.

```python
from agentchord.rag.embeddings.gemini import GeminiEmbeddings

embedder = GeminiEmbeddings(
    model="text-embedding-004",
    api_key="...",  # None이면 GOOGLE_API_KEY 환경 변수 사용
    dimensions=768,
)
```

> 배치 처리 시 최대 100개씩 자동 분할됩니다.

---

## 벡터 저장소

### VectorStore (추상 기본 클래스)

**추상 메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `add` | `async add(chunks: list[Chunk]) -> list[str]` | `list[str]` | 임베딩이 포함된 청크 추가 |
| `search` | `async search(query_embedding: list[float], limit: int = 10, filter: dict \| None = None) -> list[SearchResult]` | `list[SearchResult]` | 유사 벡터 검색 |
| `delete` | `async delete(chunk_ids: list[str]) -> int` | `int` | ID로 청크 삭제 |
| `clear` | `async clear() -> None` | `None` | 모든 벡터 삭제 |
| `count` | `async count() -> int` | `int` | 저장된 벡터 수 |
| `get` | `async get(chunk_id: str) -> Chunk \| None` | `Chunk \| None` | ID로 청크 조회 |

---

### InMemoryVectorStore

메모리 내 코사인 유사도 기반 벡터 저장소입니다. 의존성 없이 즉시 사용 가능합니다.

```python
from agentchord.rag.vectorstore.in_memory import InMemoryVectorStore

store = InMemoryVectorStore()
ids = await store.add(chunks_with_embeddings)
results = await store.search(query_vector, limit=5)
```

> 대용량 데이터는 ChromaDB 또는 FAISS 사용을 권장합니다.

---

### ChromaVectorStore

ChromaDB를 사용하는 영구 벡터 저장소입니다.

```python
from agentchord.rag.vectorstore.chroma import ChromaVectorStore

store = ChromaVectorStore(
    collection_name="my-docs",
    persist_directory="./chroma_db",
)
```

> `chromadb` 필요: `pip install agentchord[rag]`

---

### FAISSVectorStore

FAISS를 사용하는 고성능 벡터 저장소입니다.

```python
from agentchord.rag.vectorstore.faiss import FAISSVectorStore

store = FAISSVectorStore(
    dimensions=1536,
    index_type="flat",  # "flat" 또는 "ivf"
)
```

> `faiss-cpu` 필요: `pip install agentchord[rag-full]`

---

## 검색

### BM25Search

Okapi BM25 알고리즘 기반 희소(sparse) 키워드 검색입니다.

```python
from agentchord.rag.search.bm25 import BM25Search

bm25 = BM25Search(k1=1.5, b=0.75)

# 인덱스 구축
bm25.index(chunks)

# 검색
results = bm25.search("error handling", limit=10)

# 증분 업데이트
bm25.add_chunks(new_chunks)
bm25.remove_chunks(["chunk_id_1", "chunk_id_2"])
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `k1` | `float` | `1.5` | 단어 빈도 포화 파라미터. 높을수록 빈도 효과 증가 |
| `b` | `float` | `0.75` | 문서 길이 정규화. 0=정규화 없음, 1=완전 정규화 |
| `stop_words` | `frozenset[str] \| None` | 기본 영어 불용어 | 인덱싱/검색에서 제외할 단어 |

**메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `index` | `index(chunks: list[Chunk]) -> None` | `None` | 청크로 BM25 인덱스 구축 (기존 인덱스 교체) |
| `search` | `search(query: str, limit: int = 10) -> list[SearchResult]` | `list[SearchResult]` | 키워드 기반 검색 |
| `add_chunks` | `add_chunks(chunks: list[Chunk]) -> None` | `None` | 기존 인덱스에 청크 추가 |
| `remove_chunks` | `remove_chunks(chunk_ids: list[str]) -> int` | `int` | ID로 청크 제거. 제거된 수 반환 |

> BM25 점수 공식: `Σ IDF(qi) × f(qi,D)×(k1+1) / (f(qi,D) + k1×(1−b+b×|D|/avgdl))`

---

### HybridSearch

밀집(dense) 벡터 검색과 BM25 희소 검색을 결합하는 하이브리드 검색입니다. RRF(Reciprocal Rank Fusion) 알고리즘으로 결과를 융합합니다.

```python
from agentchord.rag.search.hybrid import HybridSearch

hybrid = HybridSearch(
    vectorstore=InMemoryVectorStore(),
    embedding_provider=OpenAIEmbeddings(),
    bm25=BM25Search(),
    rrf_k=60,
)

await hybrid.add(chunks)
result = await hybrid.search("쿼리", limit=5)
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `vectorstore` | `VectorStore` | 필수 | 밀집 검색용 벡터 저장소 |
| `embedding_provider` | `EmbeddingProvider` | 필수 | 쿼리 벡터화용 임베딩 프로바이더 |
| `bm25` | `BM25Search \| None` | `None` | 희소 검색용 BM25 인덱스. None이면 빈 BM25 생성 |
| `reranker` | `Reranker \| None` | `None` | 2단계 리랭커 |
| `rrf_k` | `int` | `60` | RRF 스무딩 상수. 높을수록 균일한 가중치 |
| `vector_weight` | `float` | `1.0` | 벡터 검색 RRF 점수 가중치 |
| `bm25_weight` | `float` | `1.0` | BM25 RRF 점수 가중치 |
| `vector_candidates` | `int` | `25` | 벡터 검색에서 가져올 후보 수 |
| `bm25_candidates` | `int` | `25` | BM25 검색에서 가져올 후보 수 |

> RRF 공식: `rrf_score(d) = Σ 1 / (k + rank_i(d))`

---

## 평가

### RAGEvaluator

RAG 파이프라인 품질을 RAGAS 스타일 메트릭으로 평가합니다.

```python
from agentchord.rag.evaluation.evaluator import RAGEvaluator

evaluator = RAGEvaluator(llm=provider)

result = await evaluator.evaluate(
    query="AgentChord란 무엇인가요?",
    answer="AgentChord는 멀티 에이전트 프레임워크입니다.",
    contexts=["AgentChord는 Python 기반 멀티 에이전트 오케스트레이션 프레임워크입니다."],
)

print(f"RAGAS 점수: {result.ragas_score:.2f}")
for metric in result.metrics:
    print(f"  {metric.name}: {metric.score:.2f}")
```

**생성자 파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `llm` | `BaseLLMProvider` | 필수 | 메트릭 평가용 LLM 프로바이더 |
| `metrics` | `list[BaseMetric] \| None` | `None` | 커스텀 메트릭. None이면 기본 3개 메트릭 사용 |

**기본 메트릭 (3개):**

| 메트릭 | 설명 |
|--------|------|
| `Faithfulness` | 답변이 컨텍스트에 근거하는지 평가 (허구 탐지) |
| `AnswerRelevancy` | 답변이 질문과 관련 있는지 평가 |
| `ContextRelevancy` | 컨텍스트가 질문에 관련 있는지 평가 |

**메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `evaluate` | `async evaluate(query: str, answer: str, contexts: list[str]) -> EvaluationResult` | `EvaluationResult` | 모든 메트릭으로 평가 실행 |
| `evaluate_response` | `async evaluate_response(response: RAGResponse) -> EvaluationResult` | `EvaluationResult` | RAGResponse로 직접 평가 |
| `add_metric` | `add_metric(metric: BaseMetric) -> None` | `None` | 커스텀 메트릭 추가 |

---

### EvaluationResult

평가 결과 데이터클래스입니다.

**필드:**

| 필드 | 타입 | 설명 |
|------|------|------|
| `metrics` | `list[MetricResult]` | 개별 메트릭 결과 목록 |

**프로퍼티:**

| 프로퍼티 | 타입 | 설명 |
|----------|------|------|
| `ragas_score` | `float` | 모든 메트릭의 조화 평균 (0~1) |

**메서드:**

| 메서드 | 시그니처 | 반환값 | 설명 |
|--------|---------|--------|------|
| `get_metric` | `get_metric(name: str) -> MetricResult \| None` | `MetricResult \| None` | 이름으로 특정 메트릭 결과 조회 |
| `summary` | `summary() -> dict[str, float]` | `dict[str, float]` | 모든 메트릭 점수 요약 딕셔너리 반환 |

> RAGAS 점수 = 조화 평균 = n / Σ(1/score). 조화 평균은 낮은 점수를 더 강하게 페널티하여 모든 메트릭이 고르게 좋아야 높은 점수를 얻습니다.

---

## Agentic RAG

에이전트가 도구 호출로 RAG 검색을 자율적으로 결정합니다.

```python
from agentchord import Agent
from agentchord.rag import RAGPipeline
from agentchord.rag.tools import create_rag_tools
from agentchord.rag.loaders.text import TextLoader
from agentchord.rag.embeddings.openai import OpenAIEmbeddings
from agentchord.llm.openai import OpenAIProvider

# RAG 파이프라인 준비
pipeline = RAGPipeline(
    llm=OpenAIProvider(model="gpt-4o-mini"),
    embedding_provider=OpenAIEmbeddings(),
)
await pipeline.ingest([
    TextLoader("docs/readme.md"),
    TextLoader("docs/api.md"),
])

# 에이전트에 RAG 도구 등록
agent = Agent(
    name="knowledge-agent",
    role="지식 베이스를 활용하는 AI 어시스턴트",
    model="gpt-4o-mini",
    tools=create_rag_tools(pipeline, search_limit=5),
)

# 에이전트가 필요 시 자동으로 rag_search 도구 호출
result = await agent.run("AgentChord의 아키텍처를 설명해주세요")
print(result.output)
```

### create_rag_tools

RAGPipeline에서 에이전트용 도구 목록을 생성합니다.

```python
from agentchord.rag.tools import create_rag_tools

tools = create_rag_tools(pipeline, search_limit=5)
```

**파라미터:**

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `pipeline` | `RAGPipeline` | 필수 | 문서가 수집된 파이프라인 |
| `search_limit` | `int` | `5` | 기본 검색 결과 수 |

**반환값:** `list[Tool]` - 에이전트에 등록 가능한 도구 목록

> 생성되는 도구: `rag_search(query: str, limit: int)` - 지식 베이스에서 관련 정보를 검색합니다.

**Static RAG vs Agentic RAG:**

| 비교 | Static RAG | Agentic RAG |
|------|-----------|-------------|
| 검색 시점 | 매 쿼리마다 항상 검색 | 에이전트가 필요 시에만 검색 |
| 유연성 | 낮음 | 높음 |
| 토큰 효율 | 낮음 | 높음 |
| 사용 방법 | `pipeline.query()` | `agent.run()` + `create_rag_tools()` |

---

## 종합 사용 예제

```python
import asyncio
from agentchord.rag import RAGPipeline
from agentchord.rag.loaders.text import TextLoader
from agentchord.rag.loaders.web import WebLoader
from agentchord.rag.chunking.recursive import RecursiveCharacterChunker
from agentchord.rag.embeddings.openai import OpenAIEmbeddings
from agentchord.rag.vectorstore.in_memory import InMemoryVectorStore
from agentchord.rag.evaluation.evaluator import RAGEvaluator
from agentchord.llm.openai import OpenAIProvider

async def main():
    llm = OpenAIProvider(model="gpt-4o-mini")
    embedder = OpenAIEmbeddings(model="text-embedding-3-small")

    # 파이프라인 구성
    async with RAGPipeline(
        llm=llm,
        embedding_provider=embedder,
        vectorstore=InMemoryVectorStore(),
        chunker=RecursiveCharacterChunker(chunk_size=500, chunk_overlap=50),
        search_limit=5,
        enable_bm25=True,
    ) as pipeline:

        # 문서 수집
        count = await pipeline.ingest([
            TextLoader("docs/readme.md"),
            WebLoader("https://docs.agentchord.dev/"),
        ])
        print(f"{count}개 청크 수집 완료")

        # 질의
        response = await pipeline.query(
            "AgentChord의 주요 기능은?",
            limit=5,
            temperature=0.3,
        )
        print(f"답변: {response.answer}")
        print(f"참조 문서 수: {len(response.source_documents)}")
        print(f"토큰 사용: {response.usage}")

        # 품질 평가
        evaluator = RAGEvaluator(llm=llm)
        eval_result = await evaluator.evaluate_response(response)
        print(f"\nRAGAS 점수: {eval_result.ragas_score:.2f}")
        for m in eval_result.metrics:
            print(f"  {m.name}: {m.score:.2f}")

asyncio.run(main())
```
