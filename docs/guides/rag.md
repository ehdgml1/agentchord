# RAG Pipeline Guide

Retrieval-Augmented Generation (RAG) combines document retrieval with LLM generation to ground AI responses in factual context. AgentWeave provides a complete RAG system with document loading, chunking, embedding, vector search, hybrid search, reranking, and evaluation.

## Quick Start

Basic RAG pipeline with OpenAI embeddings:

```python
from agentweave.rag import RAGPipeline, OpenAIEmbeddings, InMemoryVectorStore
from agentweave import Agent

# Setup RAG pipeline
from agentweave.llm import OpenAIProvider

embeddings = OpenAIEmbeddings(api_key="your-key")
llm = OpenAIProvider(api_key="your-key", model="gpt-4o-mini")
pipeline = RAGPipeline(
    llm=llm,
    embedding_provider=embeddings
)

# Ingest documents using loaders
from agentweave.rag import TextLoader
loaders = [
    TextLoader("doc1.txt"),
    TextLoader("doc2.txt"),
]
await pipeline.ingest(loaders)

# Query with context
result = await pipeline.query(
    question="What is AgentWeave?",
    limit=3
)
print(result.answer)  # Uses retrieved documents as context
```

## Installation

Install RAG dependencies:

```bash
# Basic RAG (OpenAI embeddings + in-memory vector store)
pip install agentweave[rag]

# Full RAG (includes ChromaDB, FAISS, PDF/web loaders, rerankers)
pip install agentweave[rag-full]
```

The `[rag]` extra includes:
- OpenAI and Ollama embeddings
- In-memory vector store
- Text and directory loaders
- Basic chunking strategies

The `[rag-full]` extra adds:
- ChromaDB and FAISS vector stores
- PDF loader (pypdf)
- Web loader (beautifulsoup4)
- SentenceTransformer embeddings
- CrossEncoder reranking

## Document Loaders

Load documents from various sources.

### TextLoader

Load plain text files:

```python
from agentweave.rag import TextLoader

loader = TextLoader(file_path="knowledge.txt")
documents = await loader.load()
# Returns: [Document(content="...", metadata={"source": "knowledge.txt"})]
```

### PDFLoader

Extract text from PDFs (requires `[rag-full]`):

```python
from agentweave.rag import PDFLoader

loader = PDFLoader(file_path="research.pdf")
documents = await loader.load()
# One Document per PDF page
```

### WebLoader

Scrape web pages (requires `[rag-full]`):

```python
from agentweave.rag import WebLoader

loader = WebLoader(url="https://example.com/article")
documents = await loader.load()
# Returns: [Document(content="...", metadata={"source": "https://..."})]
```

### DirectoryLoader

Recursively load all text files from a directory:

```python
from agentweave.rag import DirectoryLoader

loader = DirectoryLoader(
    directory="./docs",
    file_pattern="*.md",
    recursive=True
)
documents = await loader.load()
# One Document per file
```

## Chunking Strategies

Split documents into smaller chunks for embedding and retrieval.

### RecursiveCharacterChunker

Split by characters with overlap:

```python
from agentweave.rag import RecursiveCharacterChunker

chunker = RecursiveCharacterChunker(
    chunk_size=500,
    chunk_overlap=50
)
chunks = await chunker.chunk(document)
# Returns: [Chunk(...), Chunk(...), ...]
```

Respects natural boundaries (paragraphs, sentences) when possible.

### SemanticChunker

Chunk by semantic similarity (requires `[rag-full]`):

```python
from agentweave.rag import SemanticChunker, OpenAIEmbeddings

embeddings = OpenAIEmbeddings(api_key="your-key")
chunker = SemanticChunker(
    embeddings=embeddings,
    similarity_threshold=0.5
)
chunks = await chunker.chunk(document)
# Splits where semantic similarity drops below threshold
```

Produces variable-length chunks based on semantic coherence.

### ParentChildChunker

Create small chunks for retrieval, large chunks for context:

```python
from agentweave.rag import ParentChildChunker

chunker = ParentChildChunker(
    parent_chunk_size=1000,
    child_chunk_size=200,
    child_overlap=20
)
chunks = await chunker.chunk(document)
# Each child chunk links to its parent via metadata
```

Retrieve small chunks (precise), but return full parent chunk (context-rich).

## Embedding Providers

Convert text to vector embeddings.

### OpenAIEmbeddings

Use OpenAI embedding models:

```python
from agentweave.rag import OpenAIEmbeddings

embeddings = OpenAIEmbeddings(
    api_key="your-key",
    model="text-embedding-3-small",
    dimensions=1536
)

vector = await embeddings.embed("Hello world")
# Returns: [0.123, -0.456, ..., 0.789]  (1536 dims)

vectors = await embeddings.embed_batch(["Doc 1", "Doc 2", "Doc 3"])
# Returns: [[...], [...], [...]]
```

### OllamaEmbeddings

Use local Ollama models:

```python
from agentweave.rag import OllamaEmbeddings

embeddings = OllamaEmbeddings(
    model="nomic-embed-text",
    base_url="http://localhost:11434"
)

vector = await embeddings.embed("Hello world")
```

### SentenceTransformerEmbeddings

Use local SentenceTransformer models (requires `[rag-full]`):

```python
from agentweave.rag import SentenceTransformerEmbeddings

embeddings = SentenceTransformerEmbeddings(
    model_name="all-MiniLM-L6-v2"
)

vector = await embeddings.embed("Hello world")
# Runs locally, no API key needed
```

## Vector Stores

Store and retrieve embeddings.

### InMemoryVectorStore

Fast in-memory storage (good for development):

```python
from agentweave.rag import InMemoryVectorStore, Chunk

vector_store = InMemoryVectorStore()

# Add chunks with embeddings
chunks = [
    Chunk(content="Doc 1", embedding=[0.1, 0.2, ...]),
    Chunk(content="Doc 2", embedding=[0.3, 0.4, ...])
]
chunk_ids = await vector_store.add(chunks)

# Search by similarity
query_embedding = [0.15, 0.25, ...]
results = await vector_store.search(query_embedding, limit=5)
for result in results:
    print(f"{result.chunk.content} (score: {result.score})")

# Get count
count = await vector_store.count()

# Get by ID
chunk = await vector_store.get(chunk_ids[0])

# Clear all
await vector_store.clear()
```

### ChromaVectorStore

Persistent vector database (requires `[rag-full]`):

```python
from agentweave.rag import ChromaVectorStore, Chunk

vector_store = ChromaVectorStore(
    collection_name="knowledge_base",
    persist_directory="./chroma_db"
)

# Add chunks with embeddings
chunks = [Chunk(content="Doc", embedding=[0.1, ...])]
await vector_store.add(chunks)

# Search by embedding
query_embedding = [0.15, ...]
results = await vector_store.search(query_embedding, limit=5)
```

### FAISSVectorStore

High-performance vector search (requires `[rag-full]`):

```python
from agentweave.rag import FAISSVectorStore, Chunk

vector_store = FAISSVectorStore(dimensions=1536, index_type="flat")

# Add chunks with embeddings
chunks = [Chunk(content="Doc", embedding=[0.1, ...] * 1536)]
await vector_store.add(chunks)

# Search by embedding
query_embedding = [0.15, ...] * 1536
results = await vector_store.search(query_embedding, limit=5)
```

## Search Strategies

### BM25Search

Pure Python keyword search (Okapi BM25 algorithm):

```python
from agentweave.rag import BM25Search, RecursiveCharacterChunker

# Create chunks
chunker = RecursiveCharacterChunker(chunk_size=500)
chunks = chunker.chunk_many(documents)

# Index with BM25
search = BM25Search(k1=1.5, b=0.75)
search.index(chunks)

# Search (sync method)
results = search.search("query", limit=5)
for result in results:
    print(f"{result.chunk.content} (score: {result.score})")
```

BM25 is good for keyword matching and doesn't require embeddings.

### HybridSearch

Combine semantic (vector) and keyword (BM25) search using Reciprocal Rank Fusion:

```python
from agentweave.rag import HybridSearch, InMemoryVectorStore, OpenAIEmbeddings, BM25Search

embeddings = OpenAIEmbeddings(api_key="your-key")
vector_store = InMemoryVectorStore()
bm25 = BM25Search()

search = HybridSearch(
    vectorstore=vector_store,
    embedding_provider=embeddings,
    bm25=bm25,
    rrf_k=60  # RRF parameter
)

# Add chunks (automatically embeds if needed)
chunks = [Chunk(content="Doc 1"), Chunk(content="Doc 2")]
await search.add(chunks)

# Combines vector similarity and BM25 keyword match
result = await search.search("query", limit=5)
print(result.results)  # RetrievalResult with timing metrics
```

Hybrid search often outperforms semantic-only or keyword-only approaches.

## Reranking

Rerank retrieved results for improved relevance.

### CrossEncoderReranker

Use cross-encoder models (requires `[rag-full]`):

```python
from agentweave.rag import CrossEncoderReranker

reranker = CrossEncoderReranker(
    model_name="cross-encoder/ms-marco-MiniLM-L-6-v2"
)

# Rerank search results
reranked = await reranker.rerank(
    query="What is Python?",
    results=search_results,
    top_n=3
)
```

Cross-encoders provide more accurate relevance scores but are slower.

### LLMReranker

Use an LLM to rerank results:

```python
from agentweave.rag import LLMReranker
from agentweave.llm import OpenAIProvider

llm = OpenAIProvider(api_key="your-key", model="gpt-4o-mini")
reranker = LLMReranker(llm_provider=llm)

reranked = await reranker.rerank(
    query="What is Python?",
    results=search_results,
    top_n=3
)
```

## RAG Pipeline

Complete end-to-end RAG workflow.

### Basic Pipeline

```python
from agentweave.rag import RAGPipeline, InMemoryVectorStore, OpenAIEmbeddings, TextLoader
from agentweave.llm import OpenAIProvider

embeddings = OpenAIEmbeddings(api_key="your-key")
llm = OpenAIProvider(api_key="your-key", model="gpt-4o-mini")

pipeline = RAGPipeline(
    llm=llm,
    embedding_provider=embeddings
)

# Ingest documents from loaders
loaders = [TextLoader("doc1.txt"), TextLoader("doc2.txt")]
await pipeline.ingest(loaders)

# Query
result = await pipeline.query(
    question="What is the answer?",
    limit=5
)
print(result.answer)
print(result.retrieval.contexts)  # Retrieved documents
```

### Advanced Pipeline

With chunking, hybrid search, and reranking:

```python
from agentweave.rag import (
    RAGPipeline, OpenAIEmbeddings, InMemoryVectorStore,
    RecursiveCharacterChunker, CrossEncoderReranker, TextLoader
)
from agentweave.llm import OpenAIProvider

# Setup components
embeddings = OpenAIEmbeddings(api_key="your-key")
llm = OpenAIProvider(api_key="your-key", model="gpt-4o")
vector_store = InMemoryVectorStore()
chunker = RecursiveCharacterChunker(chunk_size=500, chunk_overlap=50)
reranker = CrossEncoderReranker()

# Create pipeline
pipeline = RAGPipeline(
    llm=llm,
    embedding_provider=embeddings,
    vectorstore=vector_store,
    chunker=chunker,
    reranker=reranker,
    enable_bm25=True  # Enables hybrid search internally
)

# Load and ingest documents
loader = TextLoader("knowledge.txt")
documents = await loader.load()
await pipeline.ingest_documents(documents)

# Query with reranking
result = await pipeline.query(question="question", limit=10)
```

### Lifecycle Management

Use async context manager:

```python
async with RAGPipeline(llm=llm, embedding_provider=embeddings) as pipeline:
    await pipeline.ingest(loaders)
    result = await pipeline.query(question="question")
# Pipeline resources automatically cleaned up
```

Or manually:

```python
pipeline = RAGPipeline(llm=llm, embedding_provider=embeddings)
try:
    await pipeline.ingest(loaders)
    result = await pipeline.query(question="question")
finally:
    await pipeline.close()
```

## Agentic RAG

Create RAG tools for agent tool-calling workflows.

```python
from agentweave.rag import create_rag_tools, RAGPipeline, OpenAIEmbeddings, TextLoader
from agentweave.llm import OpenAIProvider
from agentweave import Agent

# Setup RAG pipeline
embeddings = OpenAIEmbeddings(api_key="your-key")
llm = OpenAIProvider(api_key="your-key", model="gpt-4o-mini")
pipeline = RAGPipeline(llm=llm, embedding_provider=embeddings)

# Ingest documents
loaders = [TextLoader("doc1.txt"), TextLoader("doc2.txt")]
await pipeline.ingest(loaders)

# Create tools
tools = create_rag_tools(pipeline=pipeline, search_limit=5)
# Returns: [rag_search, rag_query]

# Agent with RAG tools
agent = Agent(
    name="assistant",
    role="Helpful assistant with knowledge base",
    llm=llm,
    tools=tools
)

# Agent will call rag_search() or rag_query() when needed
result = await agent.run("What is AgentWeave?")
```

The agent decides when to search the knowledge base.

## Evaluation

Evaluate RAG pipeline quality with RAGAS-style metrics.

```python
from agentweave.rag import RAGEvaluator
from agentweave.llm import OpenAIProvider

llm = OpenAIProvider(api_key="your-key", model="gpt-4o-mini")
evaluator = RAGEvaluator(llm=llm)

# Evaluate a single response
result = await evaluator.evaluate(
    query="What is Python?",
    answer="Python is a high-level programming language.",
    contexts=["Python is a programming language created in 1991."]
)

print(f"RAGAS Score: {result.ragas_score}")  # Harmonic mean
for metric in result.metrics:
    print(f"{metric.name}: {metric.score}")
# Faithfulness, Answer Relevancy, Context Relevancy

# Or evaluate a RAGResponse directly
response = await pipeline.query(question="What is Python?")
result = await evaluator.evaluate_response(response)
```

Metrics range 0.0-1.0 (higher is better).

## Best Practices

### 1. Choose Appropriate Chunk Size

```python
# For precise retrieval (Q&A)
chunker = RecursiveCharacterChunker(chunk_size=300, chunk_overlap=30)

# For context-rich retrieval (summarization)
chunker = RecursiveCharacterChunker(chunk_size=1000, chunk_overlap=100)
```

### 2. Use Hybrid Search for Production

```python
# Enable BM25 in the pipeline for hybrid search
pipeline = RAGPipeline(
    llm=llm,
    embedding_provider=embeddings,
    enable_bm25=True
)
```

### 3. Rerank Top Results

```python
# Retrieve more, rerank to fewer
query_embedding = await embeddings.embed(query)
results = await vector_store.search(query_embedding, limit=20)
reranked = await reranker.rerank(query, results, top_n=5)
```

### 4. Add Metadata for Filtering

```python
chunks = [
    Chunk(content="Doc 1", metadata={"source": "manual", "version": "1.0"}, embedding=[...]),
    Chunk(content="Doc 2", metadata={"source": "api", "version": "2.0"}, embedding=[...])
]
await vector_store.add(chunks)

# Later filter by metadata when searching
query_embedding = [...]
results = await vector_store.search(query_embedding, limit=5, filter={"source": "manual"})
```

### 5. Monitor Retrieved Context Quality

```python
result = await pipeline.query(question="question")
for i, ctx in enumerate(result.retrieval.contexts):
    print(f"Context {i+1}: {ctx[:100]}...")
# Inspect what's being retrieved
```

## See Also

- [Tools Guide](tools.md) - Use RAG with agentic tool calling
- [Memory Guide](memory.md) - Conversation memory vs RAG
- [Agent Documentation](../api/core.md) - Agent API details
- [Examples](../examples.md) - Complete RAG examples
