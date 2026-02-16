"""Tests for document loaders."""
import pytest
from pathlib import Path

from agentweave.rag.loaders.text import TextLoader
from agentweave.rag.loaders.directory import DirectoryLoader


class TestTextLoader:
    async def test_load_file(self, tmp_path):
        file = tmp_path / "test.txt"
        file.write_text("Hello World", encoding="utf-8")
        loader = TextLoader(file)
        docs = await loader.load()
        assert len(docs) == 1
        assert docs[0].content == "Hello World"
        assert docs[0].metadata["file_name"] == "test.txt"

    async def test_load_nonexistent_raises(self):
        loader = TextLoader("/nonexistent/file.txt")
        with pytest.raises(FileNotFoundError):
            await loader.load()

    async def test_load_with_encoding(self, tmp_path):
        file = tmp_path / "utf8.txt"
        file.write_text("Korean text here", encoding="utf-8")
        loader = TextLoader(file, encoding="utf-8")
        docs = await loader.load()
        assert "Korean" in docs[0].content

    async def test_metadata_includes_file_info(self, tmp_path):
        file = tmp_path / "info.txt"
        file.write_text("content", encoding="utf-8")
        loader = TextLoader(file)
        docs = await loader.load()
        assert docs[0].metadata["file_name"] == "info.txt"
        assert docs[0].metadata["file_type"] == ".txt"
        assert docs[0].metadata["file_size"] > 0

    async def test_source_is_file_path(self, tmp_path):
        file = tmp_path / "source.txt"
        file.write_text("data", encoding="utf-8")
        loader = TextLoader(file)
        docs = await loader.load()
        assert str(file) == docs[0].source

    async def test_accepts_string_path(self, tmp_path):
        file = tmp_path / "str_path.txt"
        file.write_text("data", encoding="utf-8")
        loader = TextLoader(str(file))
        docs = await loader.load()
        assert len(docs) == 1


class TestDirectoryLoader:
    async def test_load_directory(self, tmp_path):
        (tmp_path / "a.txt").write_text("File A")
        (tmp_path / "b.txt").write_text("File B")
        (tmp_path / "c.py").write_text("# Python")
        loader = DirectoryLoader(tmp_path, glob="*.txt")
        docs = await loader.load()
        assert len(docs) == 2

    async def test_recursive_glob(self, tmp_path):
        subdir = tmp_path / "sub"
        subdir.mkdir()
        (tmp_path / "root.txt").write_text("Root")
        (subdir / "nested.txt").write_text("Nested")
        loader = DirectoryLoader(tmp_path, glob="**/*.txt")
        docs = await loader.load()
        assert len(docs) == 2

    async def test_nonexistent_directory(self):
        loader = DirectoryLoader("/nonexistent/dir")
        with pytest.raises(FileNotFoundError):
            await loader.load()

    async def test_empty_directory(self, tmp_path):
        loader = DirectoryLoader(tmp_path, glob="*.txt")
        docs = await loader.load()
        assert len(docs) == 0

    async def test_accepts_string_path(self, tmp_path):
        (tmp_path / "file.txt").write_text("data")
        loader = DirectoryLoader(str(tmp_path), glob="*.txt")
        docs = await loader.load()
        assert len(docs) == 1

    async def test_skips_directories(self, tmp_path):
        (tmp_path / "file.txt").write_text("data")
        subdir = tmp_path / "subdir.txt"  # directory with .txt extension
        subdir.mkdir()
        loader = DirectoryLoader(tmp_path, glob="*.txt")
        docs = await loader.load()
        assert len(docs) == 1  # only the actual file
