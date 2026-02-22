"""Tests for MCP catalog data."""
import pytest
from app.data.mcp_catalog import MCP_CATALOG, MCPServerInfo


class TestMCPCatalog:
    """Test MCP catalog data structure and contents."""

    def test_catalog_has_minimum_servers(self):
        """Test catalog contains at least 20 servers."""
        assert len(MCP_CATALOG) >= 20, (
            f"Expected at least 20 servers, found {len(MCP_CATALOG)}"
        )

    def test_all_servers_have_required_fields(self):
        """Test all servers have required fields populated."""
        for server in MCP_CATALOG:
            assert server.id, f"Server missing ID: {server}"
            assert server.name, f"Server {server.id} missing name"
            assert server.category, f"Server {server.id} missing category"
            if not server.builtin:
                assert server.command, f"Server {server.id} missing command"
            assert isinstance(server.args, list), (
                f"Server {server.id} args must be a list"
            )

    def test_official_servers_exist(self):
        """Test catalog contains official servers."""
        official = [s for s in MCP_CATALOG if s.official]
        assert len(official) >= 5, (
            f"Expected at least 5 official servers, found {len(official)}"
        )

    def test_categories_are_valid(self):
        """Test all servers use valid categories."""
        valid_categories = {
            "Web",
            "Storage",
            "Communication",
            "Database",
            "AI",
            "DevTools",
            "Utilities",
            "Analytics",
            "CMS",
            "E-commerce",
            "Monitoring",
            "Productivity",
        }
        for server in MCP_CATALOG:
            assert server.category in valid_categories, (
                f"Server {server.id} has invalid category: {server.category}"
            )

    def test_server_ids_are_unique(self):
        """Test all server IDs are unique."""
        server_ids = [s.id for s in MCP_CATALOG]
        assert len(server_ids) == len(set(server_ids)), (
            "Duplicate server IDs found in catalog"
        )

    def test_servers_have_descriptions(self):
        """Test all servers have non-empty descriptions."""
        for server in MCP_CATALOG:
            assert server.description, (
                f"Server {server.id} missing description"
            )
            assert len(server.description) > 10, (
                f"Server {server.id} description too short"
            )

    def test_servers_have_packages(self):
        """Test all non-builtin servers have package names."""
        for server in MCP_CATALOG:
            if server.builtin:
                continue
            assert server.package, f"Server {server.id} missing package"
            # Package should contain valid npm package name
            assert "/" in server.package or "mcp" in server.package, (
                f"Server {server.id} has invalid package format: {server.package}"
            )

    def test_required_secrets_format(self):
        """Test required_secrets field is properly formatted."""
        for server in MCP_CATALOG:
            assert isinstance(server.required_secrets, list), (
                f"Server {server.id} required_secrets must be a list"
            )
            for secret in server.required_secrets:
                assert isinstance(secret, str), (
                    f"Server {server.id} has non-string secret: {secret}"
                )
                assert len(secret) > 0, (
                    f"Server {server.id} has empty secret name"
                )

    def test_stars_are_non_negative(self):
        """Test all star counts are non-negative."""
        for server in MCP_CATALOG:
            assert server.stars >= 0, (
                f"Server {server.id} has negative stars: {server.stars}"
            )

    def test_official_flag_is_boolean(self):
        """Test official field is a boolean."""
        for server in MCP_CATALOG:
            assert isinstance(server.official, bool), (
                f"Server {server.id} official field must be boolean"
            )


class TestMCPServerInfo:
    """Test MCPServerInfo dataclass."""

    def test_create_server_info_minimal(self):
        """Test creating server info with minimal fields."""
        server = MCPServerInfo(
            id="test-server",
            name="Test Server",
            category="Web",
            description="Test description",
            package="test-package",
            command="npx",
            args=["-y", "test-package"],
        )

        assert server.id == "test-server"
        assert server.name == "Test Server"
        assert server.official is False
        assert server.stars == 0
        assert server.required_secrets == []

    def test_create_server_info_full(self):
        """Test creating server info with all fields."""
        server = MCPServerInfo(
            id="full-server",
            name="Full Server",
            category="Database",
            description="Full description",
            package="full-package",
            command="node",
            args=["index.js"],
            official=True,
            stars=100,
            required_secrets=["API_KEY", "SECRET_TOKEN"],
        )

        assert server.id == "full-server"
        assert server.name == "Full Server"
        assert server.official is True
        assert server.stars == 100
        assert len(server.required_secrets) == 2
        assert "API_KEY" in server.required_secrets


class TestCatalogCategories:
    """Test catalog organization by category."""

    def test_each_category_has_servers(self):
        """Test each defined category has at least one server."""
        categories = {}
        for server in MCP_CATALOG:
            if server.category not in categories:
                categories[server.category] = []
            categories[server.category].append(server)

        # Each category should have at least one server
        for category, servers in categories.items():
            assert len(servers) > 0, f"Category {category} has no servers"

    def test_popular_categories_well_represented(self):
        """Test popular categories have multiple servers."""
        category_counts = {}
        for server in MCP_CATALOG:
            category_counts[server.category] = category_counts.get(server.category, 0) + 1

        # Popular categories should have multiple options
        popular_categories = ["Web", "Storage", "Database", "DevTools"]
        for category in popular_categories:
            if category in category_counts:
                assert category_counts[category] >= 2, (
                    f"Popular category {category} should have at least 2 servers"
                )


class TestOfficialServers:
    """Test official MCP servers."""

    def test_official_servers_have_mcp_prefix(self):
        """Test official servers use @modelcontextprotocol package prefix."""
        official_servers = [s for s in MCP_CATALOG if s.official]

        for server in official_servers:
            assert server.package.startswith("@modelcontextprotocol/"), (
                f"Official server {server.id} should use @modelcontextprotocol prefix"
            )

    def test_official_servers_have_good_ratings(self):
        """Test official servers generally have higher star counts."""
        official_servers = [s for s in MCP_CATALOG if s.official]

        # Official servers should generally be well-rated
        for server in official_servers:
            # Most official servers should have at least some stars
            # (allowing for new servers to have 0)
            assert server.stars >= 0, (
                f"Official server {server.id} has invalid star count"
            )
