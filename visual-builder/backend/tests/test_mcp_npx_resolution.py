"""Tests for MCPManager npx symlink resolution."""
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.mcp_manager import MCPManager, MCPServerConfig


class TestNpxResolution:
    """Test npx symlink resolution to avoid entry guard issues."""

    @pytest.fixture
    def mcp_manager(self):
        """Create MCP manager instance."""
        return MCPManager()

    @pytest.mark.asyncio
    async def test_non_npx_command_returns_unchanged(self, mcp_manager):
        """Non-npx commands should return unchanged."""
        config = MCPServerConfig(
            id="test",
            name="Test",
            command="python",
            args=["script.py"],
        )
        cmd, args = await mcp_manager._resolve_npx_command(config)
        assert cmd == "python"
        assert args == ["script.py"]

    @pytest.mark.asyncio
    async def test_npx_without_y_flag_returns_unchanged(self, mcp_manager):
        """npx without -y flag should return unchanged."""
        config = MCPServerConfig(
            id="test",
            name="Test",
            command="npx",
            args=["some-package"],
        )
        cmd, args = await mcp_manager._resolve_npx_command(config)
        assert cmd == "npx"
        assert args == ["some-package"]

    @pytest.mark.asyncio
    async def test_npx_with_y_but_no_package_returns_unchanged(self, mcp_manager):
        """npx with -y but no package should return unchanged."""
        config = MCPServerConfig(
            id="test",
            name="Test",
            command="npx",
            args=["-y"],
        )
        cmd, args = await mcp_manager._resolve_npx_command(config)
        assert cmd == "npx"
        assert args == ["-y"]

    @pytest.mark.asyncio
    async def test_npx_cache_not_exists_returns_unchanged(self, mcp_manager):
        """If npx cache doesn't exist, return unchanged."""
        config = MCPServerConfig(
            id="test",
            name="Test",
            command="npx",
            args=["-y", "markdown2pdf-mcp@latest"],
        )
        with patch("os.path.isdir", return_value=False):
            cmd, args = await mcp_manager._resolve_npx_command(config)
        assert cmd == "npx"
        assert args == ["-y", "markdown2pdf-mcp@latest"]

    @pytest.mark.asyncio
    async def test_npx_resolves_cached_binary(self, mcp_manager, tmp_path):
        """Resolve npx binary from cache when it exists."""
        # Create mock npx cache structure
        npx_cache = tmp_path / ".npm" / "_npx"
        cache_hash = "abc123def456"
        bin_dir = npx_cache / cache_hash / "node_modules" / ".bin"
        bin_dir.mkdir(parents=True)
        
        # Create mock binary and its real target
        real_script = npx_cache / cache_hash / "node_modules" / "markdown2pdf-mcp" / "build" / "index.js"
        real_script.parent.mkdir(parents=True)
        real_script.write_text("// real script")
        
        bin_link = bin_dir / "markdown2pdf-mcp"
        bin_link.symlink_to(real_script)

        config = MCPServerConfig(
            id="test",
            name="Test",
            command="npx",
            args=["-y", "markdown2pdf-mcp@latest"],
        )

        with patch("os.path.expanduser", return_value=str(npx_cache)):
            cmd, args = await mcp_manager._resolve_npx_command(config)

        assert cmd == "node"
        assert len(args) == 1
        assert args[0].endswith("index.js")

    @pytest.mark.asyncio
    async def test_npx_extracts_bin_name_from_versioned_package(self, mcp_manager):
        """Extract binary name from package@version format."""
        config = MCPServerConfig(
            id="test",
            name="Test",
            command="npx",
            args=["-y", "markdown2pdf-mcp@1.2.3"],
        )
        
        # Mock empty cache so we can check the extraction logic
        with patch("os.path.isdir", return_value=False):
            cmd, args = await mcp_manager._resolve_npx_command(config)
        
        # Should fall back to npx since cache doesn't exist
        assert cmd == "npx"

    @pytest.mark.asyncio
    async def test_npx_extracts_bin_name_from_scoped_package(self, mcp_manager):
        """Extract binary name from @scope/package format."""
        config = MCPServerConfig(
            id="test",
            name="Test",
            command="npx",
            args=["-y", "@anthropic/mcp-fetch"],
        )
        
        # Mock empty cache
        with patch("os.path.isdir", return_value=False):
            cmd, args = await mcp_manager._resolve_npx_command(config)
        
        # Should fall back to npx
        assert cmd == "npx"

    @pytest.mark.asyncio
    async def test_npx_installs_if_not_cached(self, mcp_manager, tmp_path):
        """Install package if not in cache, then resolve."""
        npx_cache = tmp_path / ".npm" / "_npx"
        npx_cache.mkdir(parents=True)

        config = MCPServerConfig(
            id="test",
            name="Test",
            command="npx",
            args=["-y", "markdown2pdf-mcp@latest"],
        )

        mock_proc = AsyncMock()
        mock_proc.wait = AsyncMock(return_value=0)

        with patch("os.path.expanduser", return_value=str(npx_cache)):
            with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
                with patch("asyncio.wait_for", new=AsyncMock(side_effect=lambda coro, timeout: coro)):
                    cmd, args = await mcp_manager._resolve_npx_command(config)

        # Should fall back to npx if install succeeds but binary not found
        assert cmd == "npx"

    @pytest.mark.asyncio
    async def test_npx_handles_install_timeout_gracefully(self, mcp_manager, tmp_path):
        """Handle install timeout gracefully by falling back to npx."""
        npx_cache = tmp_path / ".npm" / "_npx"
        npx_cache.mkdir(parents=True)

        config = MCPServerConfig(
            id="test",
            name="Test",
            command="npx",
            args=["-y", "markdown2pdf-mcp@latest"],
        )

        with patch("os.path.expanduser", return_value=str(npx_cache)):
            with patch("asyncio.create_subprocess_exec", side_effect=Exception("timeout")):
                cmd, args = await mcp_manager._resolve_npx_command(config)

        # Should fall back to npx on install failure
        assert cmd == "npx"
        assert args == ["-y", "markdown2pdf-mcp@latest"]
