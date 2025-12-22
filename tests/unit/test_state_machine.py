"""
Tests for the TaskStateMachine.
"""

import pytest

from sanhedrin.core.types import TaskState
from sanhedrin.core.state_machine import (
    TaskStateMachine,
    VALID_TRANSITIONS,
    TERMINAL_STATES,
    ACTIVE_STATES,
    create_state_machine,
)
from sanhedrin.core.errors import InvalidStateTransitionError


class TestTaskStateMachine:
    """Tests for TaskStateMachine class."""

    def test_initial_state_is_submitted(self, state_machine: TaskStateMachine) -> None:
        """State machine starts in SUBMITTED state."""
        assert state_machine.current_state == TaskState.SUBMITTED

    def test_initial_state_recorded_in_history(self, state_machine: TaskStateMachine) -> None:
        """Initial state is recorded in history."""
        assert len(state_machine.history) == 1
        assert state_machine.history[0].to_state == TaskState.SUBMITTED
        assert state_machine.history[0].reason == "Initial state"

    def test_can_transition_to_working(self, state_machine: TaskStateMachine) -> None:
        """Can transition from SUBMITTED to WORKING."""
        assert state_machine.can_transition_to(TaskState.WORKING)

    def test_cannot_transition_to_invalid_state(self, state_machine: TaskStateMachine) -> None:
        """Cannot transition to invalid state from SUBMITTED."""
        assert not state_machine.can_transition_to(TaskState.INPUT_REQUIRED)

    def test_transition_to_working(self, state_machine: TaskStateMachine) -> None:
        """Successfully transition to WORKING."""
        status = state_machine.transition_to(TaskState.WORKING)

        assert state_machine.current_state == TaskState.WORKING
        assert status.state == TaskState.WORKING
        assert len(state_machine.history) == 2

    def test_transition_to_completed(self, state_machine: TaskStateMachine) -> None:
        """Transition through WORKING to COMPLETED."""
        state_machine.transition_to(TaskState.WORKING)
        state_machine.transition_to(TaskState.COMPLETED)

        assert state_machine.current_state == TaskState.COMPLETED
        assert state_machine.is_terminal

    def test_transition_to_failed(self, state_machine: TaskStateMachine) -> None:
        """Transition to FAILED state."""
        state_machine.transition_to(TaskState.WORKING)
        state_machine.transition_to(TaskState.FAILED)

        assert state_machine.current_state == TaskState.FAILED
        assert state_machine.is_failed
        assert state_machine.is_terminal

    def test_transition_with_reason(self, state_machine: TaskStateMachine) -> None:
        """Transition with reason is recorded."""
        state_machine.transition_to(TaskState.WORKING, reason="Starting processing")

        assert state_machine.history[-1].reason == "Starting processing"

    def test_invalid_transition_raises_error(self, state_machine: TaskStateMachine) -> None:
        """Invalid transition raises InvalidStateTransitionError."""
        with pytest.raises(InvalidStateTransitionError) as exc_info:
            state_machine.transition_to(TaskState.INPUT_REQUIRED)

        assert exc_info.value.from_state == TaskState.SUBMITTED
        assert exc_info.value.to_state == TaskState.INPUT_REQUIRED

    def test_terminal_state_cannot_transition(self, state_machine: TaskStateMachine) -> None:
        """Terminal states cannot transition further."""
        state_machine.transition_to(TaskState.WORKING)
        state_machine.transition_to(TaskState.COMPLETED)

        assert state_machine.get_valid_transitions() == set()
        with pytest.raises(InvalidStateTransitionError):
            state_machine.transition_to(TaskState.FAILED)

    def test_force_transition_bypasses_validation(self, state_machine: TaskStateMachine) -> None:
        """Force transition bypasses validation."""
        # Force transition to normally invalid state
        state_machine.force_transition(TaskState.COMPLETED, reason="Admin override")

        assert state_machine.current_state == TaskState.COMPLETED
        assert "[FORCED]" in state_machine.history[-1].reason

    def test_is_working_property(self, state_machine: TaskStateMachine) -> None:
        """is_working property works correctly."""
        assert not state_machine.is_working

        state_machine.transition_to(TaskState.WORKING)
        assert state_machine.is_working

        state_machine.transition_to(TaskState.COMPLETED)
        assert not state_machine.is_working

    def test_is_active_property(self, state_machine: TaskStateMachine) -> None:
        """is_active property works correctly."""
        assert state_machine.is_active  # SUBMITTED is active

        state_machine.transition_to(TaskState.WORKING)
        assert state_machine.is_active

        state_machine.transition_to(TaskState.COMPLETED)
        assert not state_machine.is_active

    def test_is_waiting_property(self, state_machine: TaskStateMachine) -> None:
        """is_waiting property works correctly."""
        state_machine.transition_to(TaskState.WORKING)
        state_machine.transition_to(TaskState.INPUT_REQUIRED)

        assert state_machine.is_waiting
        assert state_machine.requires_input

    def test_duration_property(self, state_machine: TaskStateMachine) -> None:
        """duration property returns positive value."""
        import time

        time.sleep(0.01)  # Small delay
        assert state_machine.duration > 0

    def test_get_status(self, state_machine: TaskStateMachine) -> None:
        """get_status returns correct status."""
        status = state_machine.get_status()

        assert status.state == TaskState.SUBMITTED

    def test_get_history_summary(self, state_machine: TaskStateMachine) -> None:
        """get_history_summary returns formatted history."""
        state_machine.transition_to(TaskState.WORKING)

        summary = state_machine.get_history_summary()

        assert len(summary) == 2
        assert summary[0]["from"] == "unknown"
        assert summary[0]["to"] == "submitted"
        assert summary[1]["from"] == "submitted"
        assert summary[1]["to"] == "working"

    def test_get_valid_transitions(self, state_machine: TaskStateMachine) -> None:
        """get_valid_transitions returns correct set."""
        valid = state_machine.get_valid_transitions()

        assert TaskState.WORKING in valid
        assert TaskState.COMPLETED in valid
        assert TaskState.FAILED in valid
        assert TaskState.INPUT_REQUIRED not in valid


class TestCreateStateMachine:
    """Tests for create_state_machine factory function."""

    def test_create_with_default_state(self) -> None:
        """Creates machine with default SUBMITTED state."""
        sm = create_state_machine()
        assert sm.current_state == TaskState.SUBMITTED

    def test_create_with_custom_state(self) -> None:
        """Creates machine with custom initial state."""
        sm = create_state_machine(initial_state=TaskState.WORKING)
        assert sm.current_state == TaskState.WORKING


class TestValidTransitions:
    """Tests for transition validation constants."""

    def test_submitted_can_transition_to_working(self) -> None:
        """SUBMITTED can transition to WORKING."""
        assert TaskState.WORKING in VALID_TRANSITIONS[TaskState.SUBMITTED]

    def test_working_can_transition_to_input_required(self) -> None:
        """WORKING can transition to INPUT_REQUIRED."""
        assert TaskState.INPUT_REQUIRED in VALID_TRANSITIONS[TaskState.WORKING]

    def test_terminal_states_have_no_transitions(self) -> None:
        """Terminal states have empty transition sets."""
        for state in TERMINAL_STATES:
            assert VALID_TRANSITIONS[state] == set()

    def test_active_states_include_submitted_and_working(self) -> None:
        """ACTIVE_STATES contains SUBMITTED and WORKING."""
        assert TaskState.SUBMITTED in ACTIVE_STATES
        assert TaskState.WORKING in ACTIVE_STATES
        assert TaskState.COMPLETED not in ACTIVE_STATES
