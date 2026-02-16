# RAG API Reference

Complete API reference for AgentWeave RAG (Retrieval-Augmented Generation) system: document loading, chunking, embeddings, vector stores, search, and evaluation.

## Types

### Document

A document to be processed by the RAG pipeline.

```python
from agentweave.rag import Document

doc = Document(
    content="Python is a programming language.",
    metadata={"source": "docs.txt", "page": 1}
)
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `content` | `str` | Document text content |
| `metadata` | `dict[str, Any]` | Arbitrary metadata (source, page, etc.) |

### Chunk

A chunk of a document.

```python
from agentweave.rag import Chunk

chunk = Chunk(
    content="Python is a programming language.",
    metadata={"source": "docs.txt", "chunk_index": 0},
    embedding=None
)
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `content` | `str` | Chunk text content |
| `metadata` | `dict[str, Any]` | Chunk metadata |
| `embedding` | `list[float] \| None` | Optional embedding vector |

### SearchResult

A single search result.

```python
from agentweave.rag import SearchResult, Chunk

chunk = Chunk(content="Python is a programming language.")
result = SearchResult(
    chunk=chunk,
    score=0.89,
    source="vector"
)
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `chunk` | `Chunk` | The matched chunk |
| `score` | `float` | Relevance score (higher is better) |
| `source` | `str` | Source of result ("vector", "bm25", "hybrid", "reranked") |

### RetrievalResult

Documents retrieved for a query.

```python
from agentweave.rag import RetrievalResult

result = RetrievalResult(
    query="What is Python?",
    results=[search_result1, search_result2]
)
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `query` | `str` | Original query |
| `results` | `list[SearchResult]` | Retrieved results |

### RAGResponse

Final response from RAG pipeline.

```python
from agentweave.rag import RAGResponse, RetrievalResult

retrieval = RetrievalResult(query="What is Python?", results=[...])
response = RAGResponse(
    query="What is Python?",
    answer="Python is a high-level programming language...",
    retrieval=retrieval,
    usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
    source_documents=["doc1", "doc2"]
)
```

**Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `query` | `str` | Original query |
| `answer` | `str` | Generated answer |
| `retrieval` | `RetrievalResult` | Retrieval result with contexts and timing |
| `usage` | `dict[str, int]` | Token usage statistics |
| `source_documents` | `list[str]` | List of source document IDs |

## RAGPipeline

Complete RAG workflow: ingest, retrieve, generate.

```python
from agentweave.rag import RAGPipeline, OpenAIEmbeddings
from agentweave.llm import OpenAIProvider

embeddings = OpenAIEmbeddings(api_key="your-key")
llm = OpenAIProvider(api_key="your-key", model="gpt-4o-mini")

pipeline = RAGPipeline(
    llm=llm,
    embedding_provider=embeddings,
    vectorstore=None,  # Optional (defaults to InMemoryVectorStore)
    chunker=None,  # Optional (defaults to RecursiveCharacterChunker)
    reranker=None,  # Optional
    system_prompt="...",  # Optional
    search_limit=5,  # Optional
    enable_bm25=True  # Optional
)
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `llm` | `BaseLLMProvider` | Required | LLM provider for answer generation |
| `embedding_provider` | `EmbeddingProvider` | Required | Embedding provider for vectorization |
| `vectorstore` | `VectorStore \| None` | None | Vector store backend (defaults to InMemoryVectorStore) |
| `chunker` | `Chunker \| None` | None | Document chunker (defaults to RecursiveCharacterChunker) |
| `reranker` | `Reranker \| None` | None | Optional reranker for improved precision |
| `system_prompt` | `str` | Default prompt | System prompt template with {context} placeholder |
| `search_limit` | `int` | 5 | Number of search results to use as context |
| `enable_bm25` | `bool` | True | Whether to use hybrid search with BM25 |

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `ingest` | `async ingest(loaders: list[DocumentLoader]) -> int` | `int` | Ingest documents from loaders, returns chunk count |
| `ingest_documents` | `async ingest_documents(documents: list[Document]) -> int` | `int` | Ingest Document objects, returns chunk count |
| `retrieve` | `async retrieve(query: str, limit: int \| None = None, *, filter: dict \| None = None) -> RetrievalResult` | `RetrievalResult` | Retrieve relevant documents |
| `generate` | `async generate(query: str, retrieval: RetrievalResult, *, temperature: float = 0.3, max_tokens: int = 1024) -> RAGResponse` | `RAGResponse` | Generate answer from query and retrieval |
| `query` | `async query(question: str, *, limit: int \| None = None, filter: dict \| None = None, temperature: float = 0.3, max_tokens: int = 1024) -> RAGResponse` | `RAGResponse` | End-to-end: retrieve + generate |
| `clear` | `async clear() -> None` | `None` | Clear all stored documents |
| `close` | `async close() -> None` | `None` | Cleanup resources |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `ingested_count` | `int` | Number of chunks ingested |

**Example:**

```python
from agentweave.rag import TextLoader

# Ingest from loaders
loaders = [TextLoader("doc1.txt"), TextLoader("doc2.txt")]
count = await pipeline.ingest(loaders)
print(f"Ingested {count} chunks")

# Or ingest pre-loaded documents
documents = await loaders[0].load()
count = await pipeline.ingest_documents(documents)

# Retrieve only
retrieval = await pipeline.retrieve("query", limit=5, filter={"source": "doc1.txt"})

# Generate with retrieval result
response = await pipeline.generate("query", retrieval, temperature=0.3, max_tokens=1024)

# End-to-end
result = await pipeline.query(question="query", limit=5, temperature=0.3)
print(result.answer)
print(result.retrieval.contexts)

# Cleanup
await pipeline.close()
```

## EmbeddingProvider

Abstract base class for embedding providers.

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `embed` | `async embed(text: str) -> list[float]` | `list[float]` | Embed single text |
| `embed_batch` | `async embed_batch(texts: list[str]) -> list[list[float]]` | `list[list[float]]` | Embed multiple texts |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `model_name` | `str` | Embedding model name |
| `dimensions` | `int` | Embedding vector dimensions |

### OpenAIEmbeddings

OpenAI embedding provider.

```python
from agentweave.rag import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(
    api_key="your-key",
    model="text-embedding-3-small",
    dimensions=1536
)

vector = await embeddings.embed("Hello")
vectors = await embeddings.embed_batch(["Hello", "World"])
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `api_key` | `str` | Required | OpenAI API key |
| `model` | `str` | "text-embedding-3-small" | Model name |
| `dimensions` | `int \| None` | None | Output dimensions (model-specific) |

### OllamaEmbeddings

Ollama embedding provider.

```python
from agentweave.rag import OllamaEmbeddings

embeddings = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url="http://localhost:11434"
)
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model` | `str` | Required | Ollama model name |
| `base_url` | `str` | "http://localhost:11434" | Ollama server URL |

### SentenceTransformerEmbeddings

Local SentenceTransformer embeddings (requires `[rag-full]`).

```python
from agentweave.rag import SentenceTransformerEmbeddings

embeddings = SentenceTransformerEmbeddings(
    model_name="all-MiniLM-L6-v2"
)
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model_name` | `str` | Required | HuggingFace model name |

## VectorStore

Abstract base class for vector stores.

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `add` | `async add(chunks: list[Chunk]) -> list[str]` | `list[str]` | Add chunks with embeddings, returns chunk IDs |
| `search` | `async search(query_embedding: list[float], limit: int = 10, filter: dict \| None = None) -> list[SearchResult]` | `list[SearchResult]` | Search by similarity with optional metadata filter |
| `delete` | `async delete(chunk_ids: list[str]) -> int` | `int` | Delete chunks by ID, returns count deleted |
| `clear` | `async clear() -> None` | `None` | Clear all documents |
| `count` | `async count() -> int` | `int` | Count stored documents |
| `get` | `async get(chunk_id: str) -> Chunk \| None` | `Chunk \| None` | Get a single chunk by ID |

### InMemoryVectorStore

In-memory vector store.

```python
from agentweave.rag import InMemoryVectorStore, Chunk

store = InMemoryVectorStore()

# Add chunks with embeddings
chunks = [Chunk(content="Doc 1", embedding=[0.1, 0.2, ...])]
chunk_ids = await store.add(chunks)

# Search by embedding
query_embedding = [0.15, 0.25, ...]
results = await store.search(query_embedding, limit=5, filter={"source": "manual"})

# Get by ID
chunk = await store.get(chunk_ids[0])

count = await store.count()
await store.clear()
```

**Constructor Parameters:**

No constructor parameters. Creates an empty in-memory store.

### ChromaVectorStore

ChromaDB vector store (requires `[rag-full]`).

```python
from agentweave.rag import ChromaVectorStore, Chunk

store = ChromaVectorStore(
    collection_name="knowledge",
    persist_directory="./chroma_db"
)

# Add chunks with embeddings
chunks = [Chunk(content="Doc", embedding=[0.1, ...])]
await store.add(chunks)

# Search
query_embedding = [0.15, ...]
results = await store.search(query_embedding, limit=5, filter={"version": "1.0"})
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `collection_name` | `str` | "agentweave" | Collection name |
| `persist_directory` | `str \| None` | None | Persistence directory (None = in-memory) |

### FAISSVectorStore

FAISS vector store (requires `[rag-full]`).

```python
from agentweave.rag import FAISSVectorStore, Chunk

store = FAISSVectorStore(dimensions=1536, index_type="flat")

# Add chunks with embeddings
chunks = [Chunk(content="Doc", embedding=[0.1, ...] * 1536)]
await store.add(chunks)

# Search
query_embedding = [0.15, ...] * 1536
results = await store.search(query_embedding, limit=5)
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `dimensions` | `int` | Required | Vector dimension size |
| `index_type` | `str` | "flat" | FAISS index type (currently only 'flat' supported) |

## Chunker

Abstract base class for document chunkers.

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `chunk` | `chunk(document: Document) -> list[Chunk]` | `list[Chunk]` | Chunk single document (sync) |
| `chunk_many` | `chunk_many(documents: list[Document]) -> list[Chunk]` | `list[Chunk]` | Chunk multiple documents (sync) |

### RecursiveCharacterChunker

Recursive character-based chunker.

```python
from agentweave.rag import RecursiveCharacterChunker

chunker = RecursiveCharacterChunker(
    chunk_size=500,
    chunk_overlap=50,
    separators=["\n\n", "\n", " ", ""]
)

chunks = chunker.chunk(document)
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `chunk_size` | `int` | 1000 | Target chunk size in characters |
| `chunk_overlap` | `int` | 200 | Overlap between chunks |
| `separators` | `list[str]` | ["\n\n", "\n", " ", ""] | Split separators (priority order) |

### SemanticChunker

Semantic similarity-based chunker (requires `[rag-full]`).

```python
from agentweave.rag import SemanticChunker, OpenAIEmbeddings

embeddings = OpenAIEmbeddings(api_key="your-key")
chunker = SemanticChunker(
    embeddings=embeddings,
    similarity_threshold=0.5
)
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `embeddings` | `EmbeddingProvider` | Required | Embedding provider |
| `similarity_threshold` | `float` | 0.5 | Similarity threshold for splits |

### ParentChildChunker

Parent-child chunking strategy.

```python
from agentweave.rag import ParentChildChunker

chunker = ParentChildChunker(
    parent_chunk_size=1000,
    child_chunk_size=200,
    child_overlap=20
)
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `parent_chunk_size` | `int` | Required | Parent chunk size |
| `child_chunk_size` | `int` | Required | Child chunk size |
| `child_overlap` | `int` | 0 | Child overlap |

## DocumentLoader

Abstract base class for document loaders.

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `load` | `async load() -> list[Document]` | `list[Document]` | Load documents |

### TextLoader

Load plain text files.

```python
from agentweave.rag import TextLoader

loader = TextLoader(file_path="knowledge.txt")
documents = await loader.load()
```

**Constructor Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `file_path` | `str` | Path to text file |

### PDFLoader

Load PDF files (requires `[rag-full]`).

```python
from agentweave.rag import PDFLoader

loader = PDFLoader(file_path="research.pdf")
documents = await loader.load()  # One Document per page
```

**Constructor Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `file_path` | `str` | Path to PDF file |

### WebLoader

Load web pages (requires `[rag-full]`).

```python
from agentweave.rag import WebLoader

loader = WebLoader(url="https://example.com/article")
documents = await loader.load()
```

**Constructor Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `url` | `str` | URL to scrape |

### DirectoryLoader

Recursively load text files from directory.

```python
from agentweave.rag import DirectoryLoader

loader = DirectoryLoader(
    directory="./docs",
    file_pattern="*.md",
    recursive=True
)
documents = await loader.load()
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `directory` | `str` | Required | Directory path |
| `file_pattern` | `str` | "*" | Glob pattern for files |
| `recursive` | `bool` | True | Recursive search |

## HybridSearch

Hybrid semantic + keyword search with RRF fusion.

```python
from agentweave.rag import HybridSearch, InMemoryVectorStore, OpenAIEmbeddings, BM25Search

embeddings = OpenAIEmbeddings(api_key="your-key")
vector_store = InMemoryVectorStore()
bm25 = BM25Search()

search = HybridSearch(
    vectorstore=vector_store,
    embedding_provider=embeddings,
    bm25=bm25,
    reranker=None,
    rrf_k=60,
    vector_weight=1.0,
    bm25_weight=1.0,
    vector_candidates=25,
    bm25_candidates=25
)

# Add chunks (automatically embeds if needed)
chunks = [Chunk(content="Doc 1"), Chunk(content="Doc 2")]
await search.add(chunks)

# Search returns RetrievalResult
result = await search.search("query", limit=5, filter={"source": "manual"})
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `vectorstore` | `VectorStore` | Required | Vector store for dense retrieval |
| `embedding_provider` | `EmbeddingProvider` | Required | Embedding provider for query vectorization |
| `bm25` | `BM25Search \| None` | None | BM25 index (creates empty if None) |
| `reranker` | `Reranker \| None` | None | Optional reranker |
| `rrf_k` | `int` | 60 | RRF smoothing constant |
| `vector_weight` | `float` | 1.0 | Weight multiplier for vector scores |
| `bm25_weight` | `float` | 1.0 | Weight multiplier for BM25 scores |
| `vector_candidates` | `int` | 25 | Candidates from vector search |
| `bm25_candidates` | `int` | 25 | Candidates from BM25 search |

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `add` | `async add(chunks: list[Chunk]) -> list[str]` | `list[str]` | Add chunks, returns chunk IDs |
| `search` | `async search(query: str, limit: int = 5, *, filter: dict \| None = None, use_reranker: bool = True) -> RetrievalResult` | `RetrievalResult` | Hybrid search with timing |
| `delete` | `async delete(chunk_ids: list[str]) -> int` | `int` | Delete chunks, returns count |
| `clear` | `async clear() -> None` | `None` | Clear all documents |

## BM25Search

Pure Python BM25 keyword search.

```python
from agentweave.rag import BM25Search, Chunk

search = BM25Search(k1=1.5, b=0.75)
chunks = [Chunk(content="Doc 1"), Chunk(content="Doc 2")]
search.index(chunks)
results = search.search("query", limit=5)
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `k1` | `float` | 1.5 | BM25 k1 parameter (term frequency saturation) |
| `b` | `float` | 0.75 | BM25 b parameter (length normalization) |
| `stop_words` | `frozenset[str] \| None` | None | Words to exclude (defaults to common English stop words) |

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `index` | `index(chunks: list[Chunk]) -> None` | `None` | Build index from chunks (sync, replaces existing) |
| `search` | `search(query: str, limit: int = 10) -> list[SearchResult]` | `list[SearchResult]` | Search documents (sync) |
| `add_chunks` | `add_chunks(chunks: list[Chunk]) -> None` | `None` | Add chunks (rebuilds entire index) |
| `remove_chunks` | `remove_chunks(chunk_ids: list[str]) -> int` | `int` | Remove chunks (rebuilds index), returns count |

**Properties:**

| Property | Type | Description |
|----------|------|-------------|
| `indexed_count` | `int` | Number of indexed chunks |

## Reranker

Abstract base class for rerankers.

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `rerank` | `async rerank(query: str, results: list[SearchResult], top_n: int = 3) -> list[SearchResult]` | `list[SearchResult]` | Rerank results |

### CrossEncoderReranker

Cross-encoder reranker (requires `[rag-full]`).

```python
from agentweave.rag import CrossEncoderReranker

reranker = CrossEncoderReranker(
    model_name="cross-encoder/ms-marco-MiniLM-L-6-v2",
    device="cpu"
)

reranked = await reranker.rerank(query, results, top_n=5)
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `model_name` | `str` | "cross-encoder/ms-marco-MiniLM-L-6-v2" | HuggingFace model name |
| `device` | `str` | "cpu" | Device to run on ('cpu' or 'cuda') |

### LLMReranker

LLM-based reranker.

```python
from agentweave.rag import LLMReranker
from agentweave.llm import OpenAIProvider

llm = OpenAIProvider(api_key="your-key", model="gpt-4o-mini")
reranker = LLMReranker(llm_provider=llm)

reranked = await reranker.rerank(query, results, top_n=5)
```

**Constructor Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `llm_provider` | `BaseLLMProvider` | LLM provider for scoring |

## create_rag_tools

Create RAG tools for agent tool-calling.

```python
from agentweave.rag import create_rag_tools, RAGPipeline
from agentweave import Agent

tools = create_rag_tools(pipeline=pipeline, search_limit=5)
# Returns: [rag_search, rag_query]

agent = Agent(name="qa", role="Q&A", llm=llm, tools=tools)
```

**Function Signature:**

```python
def create_rag_tools(
    pipeline: RAGPipeline,
    *,
    search_limit: int = 5
) -> list[Tool]:
    ...
```

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `pipeline` | `RAGPipeline` | Required | Configured RAG pipeline with ingested documents |
| `search_limit` | `int` | 5 | Default number of results per search |

**Returns:**

| Tool Name | Description | Parameters |
|-----------|-------------|------------|
| `rag_search` | Search the knowledge base for relevant information | `query: str, limit: int` |
| `rag_query` | Search and generate an answer from the knowledge base | `question: str` |

## RAGEvaluator

Evaluate RAG pipeline with RAGAS-style metrics.

```python
from agentweave.rag import RAGEvaluator
from agentweave.llm import OpenAIProvider

llm = OpenAIProvider(api_key="your-key", model="gpt-4o-mini")
evaluator = RAGEvaluator(llm=llm)

# Evaluate a single query
result = await evaluator.evaluate(
    query="What is Python?",
    answer="Python is a programming language",
    contexts=["Python is a programming language created in 1991"]
)

print(f"RAGAS Score: {result.ragas_score}")
for metric in result.metrics:
    print(f"{metric.name}: {metric.score}")

# Or evaluate a RAGResponse directly
response = await pipeline.query(question="What is Python?")
result = await evaluator.evaluate_response(response)
```

**Constructor Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `llm` | `BaseLLMProvider` | Required | LLM provider for metric evaluation |
| `metrics` | `list[BaseMetric] \| None` | None | Custom metrics (defaults to Faithfulness, Answer Relevancy, Context Relevancy) |

**Methods:**

| Method | Signature | Returns | Description |
|--------|-----------|---------|-------------|
| `evaluate` | `async evaluate(query: str, answer: str, contexts: list[str]) -> EvaluationResult` | `EvaluationResult` | Evaluate RAG quality for single query |
| `evaluate_response` | `async evaluate_response(response: RAGResponse) -> EvaluationResult` | `EvaluationResult` | Evaluate a RAGResponse directly |
| `add_metric` | `add_metric(metric: BaseMetric) -> None` | `None` | Add a custom metric |

**EvaluationResult Fields:**

| Field | Type | Description |
|-------|------|-------------|
| `metrics` | `list[MetricResult]` | Individual metric results |
| `ragas_score` | `float` | Harmonic mean of all metrics (0.0-1.0) |

**Metric Types:**

| Metric | Range | Description |
|--------|-------|-------------|
| `Faithfulness` | 0.0-1.0 | Answer grounded in retrieved context |
| `AnswerRelevancy` | 0.0-1.0 | Answer addresses the query |
| `ContextRelevancy` | 0.0-1.0 | Retrieved context relevant to query |
