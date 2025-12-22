"""
Tests for core types.
"""

import pytest
from datetime import datetime, timezone

from sanhedrin.core.types import (
    TaskState,
    TaskStatus,
    Message,
    Role,
    TextPart,
    DataPart,
    FilePart,
    FileInfo,
    Artifact,
    Task,
    AgentSkill,
    AgentCapabilities,
    AgentCard,
    JSONRPCRequest,
    JSONRPCResponse,
)


class TestTaskState:
    """Tests for TaskState enum."""

    def test_all_states_exist(self) -> None:
        """All expected states exist."""
        assert TaskState.SUBMITTED
        assert TaskState.WORKING
        assert TaskState.COMPLETED
        assert TaskState.FAILED
        assert TaskState.CANCELED
        assert TaskState.INPUT_REQUIRED
        assert TaskState.AUTH_REQUIRED
        assert TaskState.REJECTED
        assert TaskState.UNKNOWN

    def test_state_values(self) -> None:
        """States have correct string values."""
        assert TaskState.SUBMITTED.value == "submitted"
        assert TaskState.COMPLETED.value == "completed"


class TestTaskStatus:
    """Tests for TaskStatus model."""

    def test_minimal_status(self) -> None:
        """Create status with minimal fields."""
        status = TaskStatus(state=TaskState.SUBMITTED)

        assert status.state == TaskState.SUBMITTED

    def test_status_with_timestamps(self) -> None:
        """Create status with timestamps."""
        now = datetime.now(timezone.utc)
        status = TaskStatus(
            state=TaskState.WORKING,
            created_at=now,
            updated_at=now,
        )

        assert status.created_at == now


class TestMessage:
    """Tests for Message model."""

    def test_user_message(self) -> None:
        """Create user message."""
        msg = Message(
            role=Role.USER,
            parts=[TextPart(text="Hello")],
        )

        assert msg.role == Role.USER
        assert len(msg.parts) == 1

    def test_agent_message(self) -> None:
        """Create agent message."""
        msg = Message(
            role=Role.AGENT,
            parts=[TextPart(text="Response")],
        )

        assert msg.role == Role.AGENT

    def test_message_with_context(self) -> None:
        """Create message with context and task IDs."""
        msg = Message(
            role=Role.USER,
            parts=[TextPart(text="Hello")],
            context_id="ctx-123",
            task_id="task-456",
        )

        assert msg.context_id == "ctx-123"
        assert msg.task_id == "task-456"


class TestParts:
    """Tests for message part types."""

    def test_text_part(self) -> None:
        """Create text part."""
        part = TextPart(text="Hello, world!")

        assert part.type == "text"
        assert part.text == "Hello, world!"

    def test_data_part(self) -> None:
        """Create data part."""
        part = DataPart(
            mime_type="application/json",
            data='{"key": "value"}',
        )

        assert part.type == "data"
        assert part.mime_type == "application/json"

    def test_file_part(self) -> None:
        """Create file part."""
        file_info = FileInfo(
            name="test.py",
            mime_type="text/x-python",
        )
        part = FilePart(file=file_info)

        assert part.type == "file"
        assert part.file.name == "test.py"


class TestArtifact:
    """Tests for Artifact model."""

    def test_create_artifact(self) -> None:
        """Create artifact with parts."""
        artifact = Artifact(
            artifact_id="art-123",
            name="response",
            parts=[TextPart(text="Content")],
        )

        assert artifact.artifact_id == "art-123"
        assert artifact.name == "response"
        assert len(artifact.parts) == 1

    def test_artifact_with_metadata(self) -> None:
        """Create artifact with metadata."""
        artifact = Artifact(
            artifact_id="art-123",
            name="code",
            parts=[TextPart(text="print('hello')")],
            metadata={"language": "python"},
        )

        assert artifact.metadata["language"] == "python"


class TestTask:
    """Tests for Task model."""

    def test_create_task(self) -> None:
        """Create complete task."""
        status = TaskStatus(state=TaskState.SUBMITTED)
        message = Message(
            role=Role.USER,
            parts=[TextPart(text="Hello")],
        )

        task = Task(
            id="task-123",
            context_id="ctx-456",
            status=status,
            history=[message],
        )

        assert task.id == "task-123"
        assert task.status.state == TaskState.SUBMITTED
        assert len(task.history) == 1


class TestAgentSkill:
    """Tests for AgentSkill model."""

    def test_create_skill(self) -> None:
        """Create skill with all fields."""
        skill = AgentSkill(
            id="code-gen",
            name="Code Generation",
            description="Generate code in various languages",
            tags=["coding", "programming"],
            examples=["Write a Python function"],
        )

        assert skill.id == "code-gen"
        assert "coding" in skill.tags


class TestAgentCapabilities:
    """Tests for AgentCapabilities model."""

    def test_default_capabilities(self) -> None:
        """Default capabilities."""
        caps = AgentCapabilities()

        assert caps.streaming is False
        assert caps.push_notifications is False

    def test_custom_capabilities(self) -> None:
        """Custom capabilities."""
        caps = AgentCapabilities(
            streaming=True,
            push_notifications=True,
            state_transition_history=True,
        )

        assert caps.streaming is True
        assert caps.push_notifications is True


class TestJSONRPCRequest:
    """Tests for JSON-RPC request model."""

    def test_minimal_request(self) -> None:
        """Create minimal request."""
        request = JSONRPCRequest(
            method="test/method",
        )

        assert request.jsonrpc == "2.0"
        assert request.method == "test/method"

    def test_request_with_id(self) -> None:
        """Create request with ID."""
        request = JSONRPCRequest(
            method="test/method",
            id="req-123",
        )

        assert request.id == "req-123"

    def test_request_with_params(self) -> None:
        """Create request with parameters."""
        request = JSONRPCRequest(
            method="message/send",
            params={"message": {"role": "user"}},
            id=1,
        )

        assert request.params["message"]["role"] == "user"


class TestJSONRPCResponse:
    """Tests for JSON-RPC response model."""

    def test_success_response(self) -> None:
        """Create success response."""
        response = JSONRPCResponse(
            id="req-123",
            result={"status": "ok"},
        )

        assert response.id == "req-123"
        assert response.result["status"] == "ok"
        assert response.error is None

    def test_error_response(self) -> None:
        """Create error response."""
        response = JSONRPCResponse(
            id="req-123",
            error={
                "code": -32600,
                "message": "Invalid request",
            },
        )

        assert response.error["code"] == -32600
        assert response.result is None
