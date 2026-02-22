"""Tests for BM25 sparse search."""
from agentchord.rag.search.bm25 import BM25Search
from agentchord.rag.types import Chunk


class TestBM25Search:
    def _make_chunks(self, texts: list[str]) -> list[Chunk]:
        return [Chunk(id=f"c{i}", content=t) for i, t in enumerate(texts)]

    def test_index_and_search(self):
        bm25 = BM25Search()
        chunks = self._make_chunks([
            "Python is a programming language",
            "Java is also a programming language",
            "The weather is nice today",
        ])
        bm25.index(chunks)
        assert bm25.indexed_count == 3

        results = bm25.search("programming language")
        assert len(results) >= 2
        assert results[0].source == "bm25"

    def test_empty_search(self):
        bm25 = BM25Search()
        results = bm25.search("anything")
        assert results == []

    def test_search_no_match(self):
        bm25 = BM25Search()
        bm25.index(self._make_chunks(["hello world"]))
        results = bm25.search("xyz123abc456")
        assert results == []

    def test_scores_normalized(self):
        bm25 = BM25Search()
        bm25.index(self._make_chunks([
            "machine learning algorithms",
            "deep learning neural networks",
            "cooking recipes",
        ]))
        results = bm25.search("machine learning")
        assert results[0].score == 1.0  # top result normalized to 1.0
        for r in results:
            assert 0.0 <= r.score <= 1.0

    def test_add_chunks(self):
        bm25 = BM25Search()
        bm25.index(self._make_chunks(["hello"]))
        assert bm25.indexed_count == 1
        bm25.add_chunks([Chunk(id="new0", content="world")])
        assert bm25.indexed_count == 2

    def test_remove_chunks(self):
        bm25 = BM25Search()
        chunks = self._make_chunks(["alpha", "beta", "gamma"])
        bm25.index(chunks)
        removed = bm25.remove_chunks(["c0"])
        assert removed == 1
        assert bm25.indexed_count == 2

    def test_remove_nonexistent(self):
        bm25 = BM25Search()
        bm25.index(self._make_chunks(["hello"]))
        removed = bm25.remove_chunks(["nonexistent"])
        assert removed == 0
        assert bm25.indexed_count == 1

    def test_limit_results(self):
        bm25 = BM25Search()
        bm25.index(self._make_chunks([
            f"document about testing number {i}" for i in range(10)
        ]))
        results = bm25.search("testing document", limit=3)
        assert len(results) <= 3

    def test_custom_k1_b(self):
        bm25 = BM25Search(k1=2.0, b=0.5)
        bm25.index(self._make_chunks(["test document"]))
        results = bm25.search("test")
        assert len(results) == 1

    def test_stop_words_filtered(self):
        bm25 = BM25Search()
        bm25.index(self._make_chunks(["the cat sat on the mat"]))
        # "the" is a stop word; single-letter tokens also filtered (len > 1)
        results = bm25.search("the")
        assert results == []

    def test_empty_query(self):
        bm25 = BM25Search()
        bm25.index(self._make_chunks(["hello world"]))
        results = bm25.search("")
        assert results == []

    def test_index_replaces_previous(self):
        bm25 = BM25Search()
        bm25.index(self._make_chunks(["first batch"]))
        assert bm25.indexed_count == 1
        bm25.index(self._make_chunks(["second", "batch"]))
        assert bm25.indexed_count == 2

    def test_single_result(self):
        bm25 = BM25Search()
        bm25.index(self._make_chunks(["unique keyword xylophone"]))
        results = bm25.search("xylophone")
        assert len(results) == 1
        assert results[0].score == 1.0

    def test_custom_stop_words(self):
        bm25 = BM25Search(stop_words=frozenset({"python", "java"}))
        bm25.index(self._make_chunks(["python programming", "java development"]))
        results = bm25.search("python")
        # "python" is a stop word here, so no matches
        assert results == []
