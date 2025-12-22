"""
Tests for error types.
"""

import pytest

from sanhedrin.core.types import TaskState
from sanhedrin.core.errors import (
    ErrorCode,
    SanhedrinError,
    A2AError,
    ParseError,
    InvalidRequestError,
    MethodNotFoundError,
    InvalidParamsError,
    InternalError,
    TaskNotFoundError,
    TaskNotCancelableError,
    InvalidStateTransitionError,
    AdapterError,
    AdapterInitializationError,
    AdapterExecutionError,
    AdapterNotFoundError,
    AdapterTimeoutError,
    CLINotFoundError,
    AuthenticationRequiredError,
    AuthorizationFailedError,
)


class TestErrorCode:
    """Tests for error codes."""

    def test_standard_jsonrpc_codes(self) -> None:
        """Standard JSON-RPC error codes."""
        assert ErrorCode.PARSE_ERROR == -32700
        assert ErrorCode.INVALID_REQUEST == -32600
        assert ErrorCode.METHOD_NOT_FOUND == -32601
        assert ErrorCode.INVALID_PARAMS == -32602
        assert ErrorCode.INTERNAL_ERROR == -32603

    def test_a2a_codes(self) -> None:
        """A2A specific error codes."""
        assert ErrorCode.TASK_NOT_FOUND == -32001
        assert ErrorCode.TASK_NOT_CANCELABLE == -32002
        assert ErrorCode.AUTHENTICATION_REQUIRED == -32007


class TestSanhedrinError:
    """Tests for base error class."""

    def test_basic_error(self) -> None:
        """Create basic error."""
        error = SanhedrinError("Something went wrong")

        assert str(error) == "Something went wrong"
        assert error.code == ErrorCode.INTERNAL_ERROR

    def test_error_with_code(self) -> None:
        """Create error with custom code."""
        error = SanhedrinError("Error", code=-32001)

        assert error.code == -32001

    def test_error_with_data(self) -> None:
        """Create error with additional data."""
        error = SanhedrinError("Error", data={"detail": "more info"})

        assert error.data["detail"] == "more info"

    def test_to_dict(self) -> None:
        """Convert error to JSON-RPC format."""
        error = SanhedrinError("Error message", code=-32000, data={"key": "value"})
        result = error.to_dict()

        assert result["code"] == -32000
        assert result["message"] == "Error message"
        assert result["data"]["key"] == "value"


class TestJSONRPCErrors:
    """Tests for JSON-RPC standard errors."""

    def test_parse_error(self) -> None:
        """Parse error."""
        error = ParseError()

        assert error.code == ErrorCode.PARSE_ERROR
        assert "Parse error" in str(error)

    def test_invalid_request_error(self) -> None:
        """Invalid request error."""
        error = InvalidRequestError("Missing field: method")

        assert error.code == ErrorCode.INVALID_REQUEST

    def test_method_not_found_error(self) -> None:
        """Method not found error."""
        error = MethodNotFoundError("unknown/method")

        assert error.code == ErrorCode.METHOD_NOT_FOUND
        assert error.method == "unknown/method"
        assert "unknown/method" in str(error)

    def test_invalid_params_error(self) -> None:
        """Invalid params error."""
        error = InvalidParamsError("Missing required param")

        assert error.code == ErrorCode.INVALID_PARAMS

    def test_internal_error(self) -> None:
        """Internal error."""
        error = InternalError("Unexpected error")

        assert error.code == ErrorCode.INTERNAL_ERROR


class TestA2AErrors:
    """Tests for A2A protocol errors."""

    def test_task_not_found(self) -> None:
        """Task not found error."""
        error = TaskNotFoundError("task-123")

        assert error.code == ErrorCode.TASK_NOT_FOUND
        assert error.task_id == "task-123"
        assert "task-123" in str(error)

    def test_task_not_cancelable(self) -> None:
        """Task not cancelable error."""
        error = TaskNotCancelableError("task-123", "completed")

        assert error.code == ErrorCode.TASK_NOT_CANCELABLE
        assert error.task_id == "task-123"
        assert error.current_state == "completed"

    def test_authentication_required(self) -> None:
        """Authentication required error."""
        error = AuthenticationRequiredError()

        assert error.code == ErrorCode.AUTHENTICATION_REQUIRED

    def test_authorization_failed(self) -> None:
        """Authorization failed error."""
        error = AuthorizationFailedError("Insufficient permissions")

        assert error.code == ErrorCode.AUTHORIZATION_FAILED


class TestStateTransitionError:
    """Tests for state transition errors."""

    def test_basic_transition_error(self) -> None:
        """Basic transition error."""
        error = InvalidStateTransitionError(
            from_state=TaskState.SUBMITTED,
            to_state=TaskState.INPUT_REQUIRED,
        )

        assert error.from_state == TaskState.SUBMITTED
        assert error.to_state == TaskState.INPUT_REQUIRED
        assert "submitted" in str(error)
        assert "input-required" in str(error)

    def test_transition_error_with_valid(self) -> None:
        """Transition error with valid transitions."""
        error = InvalidStateTransitionError(
            from_state=TaskState.SUBMITTED,
            to_state=TaskState.INPUT_REQUIRED,
            valid_transitions={TaskState.WORKING, TaskState.FAILED},
        )

        assert error.valid_transitions == {TaskState.WORKING, TaskState.FAILED}
        # Valid transitions should be in message
        assert "working" in str(error) or "failed" in str(error)


class TestAdapterErrors:
    """Tests for adapter errors."""

    def test_adapter_error(self) -> None:
        """Basic adapter error."""
        error = AdapterError("test-adapter", "Something failed")

        assert error.adapter == "test-adapter"
        assert "[test-adapter]" in str(error)

    def test_initialization_error(self) -> None:
        """Adapter initialization error."""
        error = AdapterInitializationError("claude", "CLI not found")

        assert "Initialization failed" in str(error)
        assert "CLI not found" in str(error)

    def test_execution_error(self) -> None:
        """Adapter execution error."""
        error = AdapterExecutionError("claude", "Timeout", exit_code=124)

        assert error.exit_code == 124
        assert "Execution failed" in str(error)

    def test_adapter_not_found(self) -> None:
        """Adapter not found error."""
        error = AdapterNotFoundError("unknown", available=["claude", "gemini"])

        assert error.name == "unknown"
        assert error.available == ["claude", "gemini"]
        assert "unknown" in str(error)
        assert "claude" in str(error)

    def test_timeout_error(self) -> None:
        """Adapter timeout error."""
        error = AdapterTimeoutError("claude", timeout=30.0)

        assert error.timeout == 30.0
        assert "30" in str(error)

    def test_cli_not_found(self) -> None:
        """CLI not found error."""
        error = CLINotFoundError(
            "claude",
            "claude",
            install_hint="pip install claude-cli",
        )

        assert error.cli_command == "claude"
        assert error.install_hint == "pip install claude-cli"
