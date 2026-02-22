"""Integration test for markdown2pdf-mcp server connection fix.

This test verifies that the npx symlink resolution fix in MCPManager
correctly handles packages with entry guards like markdown2pdf-mcp.
"""
import pytest
import os

from app.core.mcp_manager import MCPManager, MCPServerConfig


@pytest.mark.integration
@pytest.mark.asyncio
async def test_markdown2pdf_connection_via_resolved_path():
    """Test that markdown2pdf-mcp connects successfully via resolved path.
    
    Before the fix: npx runs the .bin/markdown2pdf-mcp symlink, causing
    path.resolve(argv[1]) !== __filename, so the entry guard fails and
    server.run() never executes.
    
    After the fix: MCPManager resolves the symlink to the real path and
    uses `node <real_path>`, so argv[1] === __filename and the server starts.
    """
    manager = MCPManager()
    
    config = MCPServerConfig(
        id="markdown2pdf-test",
        name="Markdown to PDF",
        command="npx",
        args=["-y", "markdown2pdf-mcp@latest"],
    )
    
    try:
        # This should succeed with the fix
        await manager.connect(config)
        
        # Verify server is connected
        assert manager.get_server_status("markdown2pdf-test")["connected"]
        
        # Verify tools are available
        tools = manager.list_tools("markdown2pdf-test")
        assert len(tools) > 0
        
        # Check for expected tool
        tool_names = [tool.name for tool in tools]
        assert "create_pdf_from_markdown" in tool_names
        
    finally:
        # Cleanup
        await manager.disconnect("markdown2pdf-test")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_npx_resolution_uses_node_command():
    """Verify that npx resolution converts command to 'node' with real path."""
    manager = MCPManager()
    
    config = MCPServerConfig(
        id="test",
        name="Test",
        command="npx",
        args=["-y", "markdown2pdf-mcp@latest"],
    )
    
    # Check if package is cached (from previous runs or installations)
    npx_cache = os.path.expanduser("~/.npm/_npx")
    has_cache = os.path.isdir(npx_cache)
    
    if not has_cache:
        pytest.skip("npx cache not found - run npx markdown2pdf-mcp first")
    
    # Find the binary
    bin_name = "markdown2pdf-mcp"
    found_binary = False
    
    for cache_hash in os.listdir(npx_cache):
        bin_link = os.path.join(npx_cache, cache_hash, "node_modules", ".bin", bin_name)
        if os.path.exists(bin_link):
            found_binary = True
            break
    
    if not found_binary:
        pytest.skip("markdown2pdf-mcp not cached - install it first")
    
    # Resolve the command
    resolved_cmd, resolved_args = await manager._resolve_npx_command(config)
    
    # Should convert npx to node
    assert resolved_cmd == "node"
    
    # Should have exactly one arg (the real path)
    assert len(resolved_args) == 1
    
    # The path should point to the real index.js file
    assert resolved_args[0].endswith("index.js")
    assert "markdown2pdf-mcp" in resolved_args[0]
    assert os.path.isfile(resolved_args[0])
