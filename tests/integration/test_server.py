"""
Integration tests for the FastAPI server.
"""

import pytest
from unittest.mock import patch, AsyncMock, MagicMock
from fastapi.testclient import TestClient

from tests.conftest import MockAdapter


class TestServerEndpoints:
    """Integration tests for server endpoints."""

    @pytest.fixture
    def mock_adapter_class(self):
        """Create a mock adapter class that can be returned by get_adapter."""
        adapter = MockAdapter()
        return adapter

    @pytest.fixture
    def client(self, mock_adapter_class):
        """Create test client with mocked adapter."""
        with patch.dict('os.environ', {
            'SANHEDRIN_ADAPTER': 'mock-adapter',
            'SANHEDRIN_ENV': 'development',
            'SANHEDRIN_AUTH_ENABLED': 'false',
            'SANHEDRIN_RATE_LIMIT_ENABLED': 'false',
        }):
            with patch('sanhedrin.server.app.get_adapter') as mock_get:
                with patch('sanhedrin.server.app.register_default_adapters'):
                    mock_get.return_value = mock_adapter_class

                    # Import after patching
                    from sanhedrin.server.app import app

                    with TestClient(app) as client:
                        yield client

    def test_root_endpoint(self, client: TestClient) -> None:
        """Root endpoint returns server info."""
        response = client.get("/")

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Sanhedrin A2A Server"
        assert "version" in data
        assert "protocol" in data

    def test_health_endpoint(self, client: TestClient) -> None:
        """Health endpoint returns status."""
        response = client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_metrics_endpoint(self, client: TestClient) -> None:
        """Metrics endpoint returns Prometheus format."""
        response = client.get("/metrics")

        assert response.status_code == 200
        assert "sanhedrin_requests_total" in response.text
        assert "sanhedrin_tasks_created" in response.text

    def test_agent_card_endpoint(self, client: TestClient) -> None:
        """Agent card endpoint returns valid card."""
        response = client.get("/.well-known/agent.json")

        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "url" in data

    def test_a2a_invalid_json(self, client: TestClient) -> None:
        """A2A endpoint rejects invalid JSON."""
        response = client.post(
            "/a2a",
            content="not json",
            headers={"Content-Type": "application/json"},
        )

        assert response.status_code == 400

    def test_a2a_missing_method(self, client: TestClient) -> None:
        """A2A endpoint requires method field."""
        response = client.post(
            "/a2a",
            json={"jsonrpc": "2.0"},
        )

        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    def test_a2a_invalid_method(self, client: TestClient) -> None:
        """A2A endpoint rejects unknown methods."""
        response = client.post(
            "/a2a",
            json={
                "jsonrpc": "2.0",
                "method": "unknown/method",
                "id": 1,
            },
        )

        # Should return JSON-RPC error (not HTTP error)
        assert response.status_code == 200
        data = response.json()
        assert "error" in data


class TestSecurityHeaders:
    """Tests for security headers."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        with patch.dict('os.environ', {
            'SANHEDRIN_ADAPTER': 'mock-adapter',
            'SANHEDRIN_ENV': 'development',
            'SANHEDRIN_AUTH_ENABLED': 'false',
            'SANHEDRIN_RATE_LIMIT_ENABLED': 'false',
        }):
            adapter = MockAdapter()
            with patch('sanhedrin.server.app.get_adapter') as mock_get:
                with patch('sanhedrin.server.app.register_default_adapters'):
                    mock_get.return_value = adapter

                    from sanhedrin.server.app import app

                    with TestClient(app) as client:
                        yield client

    def test_security_headers_present(self, client: TestClient) -> None:
        """Security headers are added to responses."""
        response = client.get("/health")

        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"


class TestRequestLogging:
    """Tests for request logging middleware."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        with patch.dict('os.environ', {
            'SANHEDRIN_ADAPTER': 'mock-adapter',
            'SANHEDRIN_ENV': 'development',
            'SANHEDRIN_AUTH_ENABLED': 'false',
            'SANHEDRIN_RATE_LIMIT_ENABLED': 'false',
        }):
            adapter = MockAdapter()
            with patch('sanhedrin.server.app.get_adapter') as mock_get:
                with patch('sanhedrin.server.app.register_default_adapters'):
                    mock_get.return_value = adapter

                    from sanhedrin.server.app import app

                    with TestClient(app) as client:
                        yield client

    def test_request_id_header(self, client: TestClient) -> None:
        """Request ID is echoed in response."""
        response = client.get(
            "/health",
            headers={"X-Request-ID": "test-123"},
        )

        assert response.headers.get("X-Request-ID") == "test-123"

    def test_response_time_header(self, client: TestClient) -> None:
        """Response time header is added."""
        response = client.get("/health")

        assert "X-Response-Time" in response.headers
