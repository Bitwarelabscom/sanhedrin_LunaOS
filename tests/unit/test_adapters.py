"""
Tests for adapters.
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from sanhedrin.adapters.base import (
    BaseAdapter,
    AdapterConfig,
    ExecutionResult,
    StreamChunk,
)
from sanhedrin.core.types import Message, Role, TextPart, DataPart, AgentSkill

from tests.conftest import MockAdapter


class TestAdapterConfig:
    """Tests for AdapterConfig."""

    def test_default_values(self) -> None:
        """Default config has expected values."""
        config = AdapterConfig()

        assert config.timeout == 120.0
        assert config.max_retries == 3
        assert config.retry_delay == 1.0
        assert config.streaming is True

    def test_custom_values(self) -> None:
        """Config accepts custom values."""
        config = AdapterConfig(
            timeout=30.0,
            max_retries=5,
            streaming=False,
        )

        assert config.timeout == 30.0
        assert config.max_retries == 5
        assert config.streaming is False


class TestExecutionResult:
    """Tests for ExecutionResult."""

    def test_success_result(self) -> None:
        """Successful result properties."""
        result = ExecutionResult(
            success=True,
            content="Hello",
        )

        assert result.success
        assert not result.is_error
        assert result.exit_code == 0

    def test_error_result(self) -> None:
        """Error result properties."""
        result = ExecutionResult(
            success=False,
            content="",
            error="Something went wrong",
            exit_code=1,
        )

        assert not result.success
        assert result.is_error
        assert result.error == "Something went wrong"

    def test_result_with_metadata(self) -> None:
        """Result can include metadata."""
        result = ExecutionResult(
            success=True,
            content="Hello",
            metadata={"tokens": 100},
        )

        assert result.metadata["tokens"] == 100


class TestStreamChunk:
    """Tests for StreamChunk."""

    def test_text_chunk(self) -> None:
        """Text chunk properties."""
        chunk = StreamChunk(content="Hello")

        assert chunk.content == "Hello"
        assert chunk.chunk_type == "text"
        assert not chunk.is_final

    def test_final_chunk(self) -> None:
        """Final chunk properties."""
        chunk = StreamChunk(
            content="world",
            is_final=True,
        )

        assert chunk.is_final

    def test_error_chunk(self) -> None:
        """Error chunk properties."""
        chunk = StreamChunk(
            content="",
            chunk_type="error",
            metadata={"error": "Failed"},
        )

        assert chunk.chunk_type == "error"


class TestMockAdapter:
    """Tests for MockAdapter (testing the test fixture)."""

    async def test_initialize(self, mock_adapter: MockAdapter) -> None:
        """Adapter can be initialized."""
        assert not mock_adapter.is_initialized

        await mock_adapter.initialize()

        assert mock_adapter.is_initialized

    async def test_execute(self, initialized_mock_adapter: MockAdapter) -> None:
        """Adapter can execute prompts."""
        result = await initialized_mock_adapter.execute("Hello")

        assert result.success
        assert result.content == "Mock response"

    async def test_execute_with_custom_response(
        self, initialized_mock_adapter: MockAdapter
    ) -> None:
        """Adapter response can be customized."""
        initialized_mock_adapter.set_response("Custom response")

        result = await initialized_mock_adapter.execute("Hello")

        assert result.content == "Custom response"

    async def test_execute_failure(
        self, initialized_mock_adapter: MockAdapter
    ) -> None:
        """Adapter can simulate failure."""
        initialized_mock_adapter.set_should_fail(True)

        result = await initialized_mock_adapter.execute("Hello")

        assert not result.success
        assert result.error == "Mock error"

    async def test_execute_stream(
        self, initialized_mock_adapter: MockAdapter
    ) -> None:
        """Adapter can stream responses."""
        initialized_mock_adapter.set_response("Hello streaming world")

        chunks = []
        async for chunk in initialized_mock_adapter.execute_stream("Hello"):
            chunks.append(chunk)

        assert len(chunks) == 3  # "Hello ", "streaming ", "world "
        assert chunks[-1].is_final

    async def test_health_check(
        self, initialized_mock_adapter: MockAdapter
    ) -> None:
        """Adapter health check works."""
        assert await initialized_mock_adapter.health_check()

        initialized_mock_adapter.set_health(False)
        assert not await initialized_mock_adapter.health_check()

    def test_properties(self, mock_adapter: MockAdapter) -> None:
        """Adapter has required properties."""
        assert mock_adapter.name == "mock-adapter"
        assert mock_adapter.display_name == "Mock Adapter"
        assert mock_adapter.description is not None
        assert len(mock_adapter.skills) > 0


class TestBaseAdapterMethods:
    """Tests for BaseAdapter utility methods."""

    async def test_message_to_prompt_text(
        self, initialized_mock_adapter: MockAdapter
    ) -> None:
        """Convert text message to prompt."""
        message = Message(
            role=Role.USER,
            parts=[TextPart(text="Hello, world!")],
        )

        prompt = initialized_mock_adapter.message_to_prompt(message)

        assert prompt == "Hello, world!"

    async def test_message_to_prompt_multiple_parts(
        self, initialized_mock_adapter: MockAdapter
    ) -> None:
        """Convert multi-part message to prompt."""
        message = Message(
            role=Role.USER,
            parts=[
                TextPart(text="First part"),
                TextPart(text="Second part"),
            ],
        )

        prompt = initialized_mock_adapter.message_to_prompt(message)

        assert "First part" in prompt
        assert "Second part" in prompt

    async def test_result_to_parts(
        self, initialized_mock_adapter: MockAdapter
    ) -> None:
        """Convert result to message parts."""
        result = ExecutionResult(success=True, content="Response text")

        parts = initialized_mock_adapter.result_to_parts(result)

        assert len(parts) == 1
        assert parts[0].text == "Response text"

    async def test_build_context_prompt(
        self, initialized_mock_adapter: MockAdapter
    ) -> None:
        """Build context from message history."""
        context = [
            Message(role=Role.USER, parts=[TextPart(text="Hello")]),
            Message(role=Role.AGENT, parts=[TextPart(text="Hi there!")]),
        ]

        prompt = initialized_mock_adapter.build_context_prompt(context)

        assert "User: Hello" in prompt
        assert "Assistant: Hi there!" in prompt

    async def test_build_context_prompt_empty(
        self, initialized_mock_adapter: MockAdapter
    ) -> None:
        """Empty context returns empty string."""
        prompt = initialized_mock_adapter.build_context_prompt([])

        assert prompt == ""

    async def test_supports_streaming(
        self, initialized_mock_adapter: MockAdapter
    ) -> None:
        """Check streaming support."""
        assert initialized_mock_adapter.supports_streaming

    async def test_context_manager(self, mock_adapter: MockAdapter) -> None:
        """Adapter works as async context manager."""
        async with mock_adapter as adapter:
            assert adapter.is_initialized

    def test_repr(self, mock_adapter: MockAdapter) -> None:
        """Adapter has useful repr."""
        repr_str = repr(mock_adapter)

        assert "MockAdapter" in repr_str
        assert "mock-adapter" in repr_str
