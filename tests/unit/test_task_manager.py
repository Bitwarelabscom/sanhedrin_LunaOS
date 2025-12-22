"""
Tests for the TaskManager.
"""

import pytest
from unittest.mock import AsyncMock

from sanhedrin.core.types import (
    TaskState,
    Message,
    Role,
    TextPart,
)
from sanhedrin.core.errors import TaskNotFoundError, InvalidStateTransitionError
from sanhedrin.server.task_manager import TaskManager

from tests.conftest import MockAdapter


class TestTaskManager:
    """Tests for TaskManager class."""

    @pytest.fixture
    async def task_manager(self, mock_adapter: MockAdapter) -> TaskManager:
        """Create a task manager with mock adapter."""
        await mock_adapter.initialize()
        return TaskManager(mock_adapter)

    @pytest.fixture
    def sample_message(self) -> Message:
        """Create a sample message."""
        return Message(
            role=Role.USER,
            parts=[TextPart(text="Hello, world!")],
        )

    async def test_create_task(
        self, task_manager: TaskManager, sample_message: Message
    ) -> None:
        """Create a new task."""
        task = await task_manager.create_task(sample_message)

        assert task.id is not None
        assert task.status.state == TaskState.SUBMITTED
        assert len(task.history) == 1
        assert task.history[0] == sample_message

    async def test_create_task_with_context_id(
        self, task_manager: TaskManager, sample_message: Message
    ) -> None:
        """Create task with specific context ID."""
        task = await task_manager.create_task(
            sample_message,
            context_id="my-context",
        )

        assert task.context_id == "my-context"

    async def test_get_task(
        self, task_manager: TaskManager, sample_message: Message
    ) -> None:
        """Get an existing task by ID."""
        created = await task_manager.create_task(sample_message)
        retrieved = task_manager.get_task(created.id)

        assert retrieved.id == created.id

    async def test_get_task_not_found(self, task_manager: TaskManager) -> None:
        """Getting non-existent task raises error."""
        with pytest.raises(TaskNotFoundError) as exc_info:
            task_manager.get_task("nonexistent-id")

        assert "nonexistent-id" in str(exc_info.value)

    async def test_list_tasks(
        self, task_manager: TaskManager, sample_message: Message
    ) -> None:
        """List all tasks."""
        await task_manager.create_task(sample_message)
        await task_manager.create_task(sample_message)

        tasks = task_manager.list_tasks()

        assert len(tasks) == 2

    async def test_list_tasks_by_state(
        self, task_manager: TaskManager, sample_message: Message
    ) -> None:
        """List tasks filtered by state."""
        task1 = await task_manager.create_task(sample_message)
        task2 = await task_manager.create_task(sample_message)

        # Transition one to WORKING
        await task_manager.transition_state(task1.id, TaskState.WORKING)

        submitted = task_manager.list_tasks(state=TaskState.SUBMITTED)
        working = task_manager.list_tasks(state=TaskState.WORKING)

        assert len(submitted) == 1
        assert len(working) == 1

    async def test_list_tasks_with_limit(
        self, task_manager: TaskManager, sample_message: Message
    ) -> None:
        """List tasks with limit."""
        for _ in range(10):
            await task_manager.create_task(sample_message)

        tasks = task_manager.list_tasks(limit=5)

        assert len(tasks) == 5

    async def test_transition_state(
        self, task_manager: TaskManager, sample_message: Message
    ) -> None:
        """Transition task state."""
        task = await task_manager.create_task(sample_message)
        updated = await task_manager.transition_state(task.id, TaskState.WORKING)

        assert updated.status.state == TaskState.WORKING

    async def test_transition_state_with_message(
        self, task_manager: TaskManager, sample_message: Message
    ) -> None:
        """Transition state with attached message."""
        task = await task_manager.create_task(sample_message)
        status_message = Message(
            role=Role.AGENT,
            parts=[TextPart(text="Processing...")],
        )

        updated = await task_manager.transition_state(
            task.id,
            TaskState.WORKING,
            message=status_message,
        )

        assert len(updated.history) == 2

    async def test_invalid_transition(
        self, task_manager: TaskManager, sample_message: Message
    ) -> None:
        """Invalid transition raises error."""
        task = await task_manager.create_task(sample_message)

        with pytest.raises(InvalidStateTransitionError):
            await task_manager.transition_state(task.id, TaskState.INPUT_REQUIRED)

    async def test_execute_task_sync(
        self, task_manager: TaskManager, sample_message: Message, mock_adapter: MockAdapter
    ) -> None:
        """Execute task synchronously."""
        mock_adapter.set_response("Test response")
        task = await task_manager.create_task(sample_message)

        completed = await task_manager.execute_task_sync(task.id)

        assert completed.status.state == TaskState.COMPLETED
        assert len(completed.artifacts) == 1
        assert "Test response" in completed.artifacts[0].parts[0].text

    async def test_execute_task_sync_failure(
        self, task_manager: TaskManager, sample_message: Message, mock_adapter: MockAdapter
    ) -> None:
        """Execute task with failure."""
        mock_adapter.set_should_fail(True)
        task = await task_manager.create_task(sample_message)

        failed = await task_manager.execute_task_sync(task.id)

        assert failed.status.state == TaskState.FAILED

    async def test_execute_task_streaming(
        self, task_manager: TaskManager, sample_message: Message, mock_adapter: MockAdapter
    ) -> None:
        """Execute task with streaming."""
        mock_adapter.set_response("Hello streaming world")
        task = await task_manager.create_task(sample_message)

        events = []
        async for event in task_manager.execute_task(task.id):
            events.append(event)

        # Should have status updates and artifact update
        assert len(events) >= 2

        # Check final state
        final_task = task_manager.get_task(task.id)
        assert final_task.status.state == TaskState.COMPLETED

    async def test_cancel_task(
        self, task_manager: TaskManager, sample_message: Message
    ) -> None:
        """Cancel a task."""
        task = await task_manager.create_task(sample_message)
        await task_manager.transition_state(task.id, TaskState.WORKING)

        cancelled = await task_manager.cancel_task(task.id)

        assert cancelled.status.state == TaskState.CANCELED

    async def test_cleanup_completed(
        self, task_manager: TaskManager, sample_message: Message, mock_adapter: MockAdapter
    ) -> None:
        """Cleanup old completed tasks."""
        # Create and complete a task
        task = await task_manager.create_task(sample_message)
        await task_manager.execute_task_sync(task.id)

        # Should have 1 task
        assert len(task_manager) == 1

        # Cleanup with 0 max age should remove it
        cleaned = task_manager.cleanup_completed(max_age_seconds=0)

        assert cleaned == 1
        assert len(task_manager) == 0

    async def test_task_manager_len(
        self, task_manager: TaskManager, sample_message: Message
    ) -> None:
        """TaskManager length returns task count."""
        assert len(task_manager) == 0

        await task_manager.create_task(sample_message)
        assert len(task_manager) == 1

        await task_manager.create_task(sample_message)
        assert len(task_manager) == 2
