"""
Pytest configuration and fixtures for Sanhedrin tests.
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, Iterator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from sanhedrin.core.types import (
    TaskState,
    TaskStatus,
    Message,
    Role,
    TextPart,
    AgentSkill,
)
from sanhedrin.core.state_machine import TaskStateMachine
from sanhedrin.adapters.base import (
    BaseAdapter,
    AdapterConfig,
    ExecutionResult,
    StreamChunk,
)


@pytest.fixture(scope="session")
def event_loop() -> Iterator[asyncio.AbstractEventLoop]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_message() -> Message:
    """Create a sample user message."""
    return Message(
        role=Role.USER,
        parts=[TextPart(text="Hello, world!")],
    )


@pytest.fixture
def sample_agent_message() -> Message:
    """Create a sample agent message."""
    return Message(
        role=Role.AGENT,
        parts=[TextPart(text="Hello! How can I help you?")],
    )


@pytest.fixture
def sample_skill() -> AgentSkill:
    """Create a sample skill."""
    return AgentSkill(
        id="code-generation",
        name="Code Generation",
        description="Generate code in various languages",
        tags=["coding", "programming"],
    )


@pytest.fixture
def state_machine() -> TaskStateMachine:
    """Create a fresh state machine."""
    return TaskStateMachine()


class MockAdapter(BaseAdapter):
    """Mock adapter for testing."""

    def __init__(self, config: AdapterConfig | None = None) -> None:
        super().__init__(config)
        self._response = "Mock response"
        self._should_fail = False
        self._health = True

    @property
    def name(self) -> str:
        return "mock-adapter"

    @property
    def display_name(self) -> str:
        return "Mock Adapter"

    @property
    def description(self) -> str:
        return "A mock adapter for testing"

    @property
    def skills(self) -> list[AgentSkill]:
        return [
            AgentSkill(
                id="mock-skill",
                name="Mock Skill",
                description="A mock skill",
            )
        ]

    async def initialize(self) -> None:
        self._initialized = True

    async def execute(
        self,
        prompt: str,
        context: list[Message] | None = None,
        **kwargs,
    ) -> ExecutionResult:
        if self._should_fail:
            return ExecutionResult(
                success=False,
                content="",
                error="Mock error",
                exit_code=1,
            )
        return ExecutionResult(
            success=True,
            content=self._response,
            metadata={"prompt_length": len(prompt)},
        )

    async def execute_stream(
        self,
        prompt: str,
        context: list[Message] | None = None,
        **kwargs,
    ) -> AsyncIterator[StreamChunk]:
        if self._should_fail:
            yield StreamChunk(
                content="",
                chunk_type="error",
                metadata={"error": "Mock error"},
            )
            return

        words = self._response.split()
        for i, word in enumerate(words):
            yield StreamChunk(
                content=word + " ",
                is_final=(i == len(words) - 1),
            )

    async def health_check(self) -> bool:
        return self._health

    def set_response(self, response: str) -> None:
        """Set the mock response."""
        self._response = response

    def set_should_fail(self, should_fail: bool) -> None:
        """Set whether the mock should fail."""
        self._should_fail = should_fail

    def set_health(self, healthy: bool) -> None:
        """Set health status."""
        self._health = healthy


@pytest.fixture
def mock_adapter() -> MockAdapter:
    """Create a mock adapter."""
    adapter = MockAdapter()
    return adapter


@pytest.fixture
async def initialized_mock_adapter(mock_adapter: MockAdapter) -> MockAdapter:
    """Create and initialize a mock adapter."""
    await mock_adapter.initialize()
    return mock_adapter


@pytest.fixture
def adapter_config() -> AdapterConfig:
    """Create adapter config."""
    return AdapterConfig(
        timeout=30.0,
        max_retries=2,
        retry_delay=0.1,
    )
