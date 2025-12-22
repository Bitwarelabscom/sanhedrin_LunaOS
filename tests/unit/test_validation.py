"""
Tests for input validation utilities.
"""

import pytest

from sanhedrin.utils.validation import (
    ValidationError,
    ValidationResult,
    InputValidator,
    validate_prompt_length,
    validate_task_id,
    validate_context_id,
    validate_url,
    validate_api_key,
    sanitize_prompt,
    sanitize_html,
    MAX_PROMPT_LENGTH,
)


class TestValidatePromptLength:
    """Tests for prompt length validation."""

    def test_valid_prompt(self) -> None:
        """Valid prompt passes."""
        result = validate_prompt_length("Hello, world!")
        assert result.valid
        assert result.sanitized_value == "Hello, world!"

    def test_empty_prompt(self) -> None:
        """Empty prompt is valid."""
        result = validate_prompt_length("")
        assert result.valid

    def test_prompt_too_long(self) -> None:
        """Prompt exceeding max length fails."""
        long_prompt = "x" * (MAX_PROMPT_LENGTH + 1)
        result = validate_prompt_length(long_prompt)
        assert not result.valid
        assert "exceeds maximum" in result.error

    def test_prompt_at_max_length(self) -> None:
        """Prompt at exactly max length passes."""
        exact_prompt = "x" * MAX_PROMPT_LENGTH
        result = validate_prompt_length(exact_prompt)
        assert result.valid

    def test_custom_max_length(self) -> None:
        """Custom max length is respected."""
        result = validate_prompt_length("12345", max_length=3)
        assert not result.valid

    def test_non_string_fails(self) -> None:
        """Non-string input fails."""
        result = validate_prompt_length(123)  # type: ignore
        assert not result.valid
        assert "must be a string" in result.error


class TestSanitizePrompt:
    """Tests for prompt sanitization."""

    def test_removes_null_bytes(self) -> None:
        """Null bytes are removed."""
        result = sanitize_prompt("hello\x00world")
        assert "\x00" not in result
        assert result == "helloworld"

    def test_removes_control_characters(self) -> None:
        """Control characters are removed."""
        result = sanitize_prompt("hello\x01\x02world")
        assert result == "helloworld"

    def test_preserves_newlines(self) -> None:
        """Newlines are preserved."""
        result = sanitize_prompt("hello\nworld")
        assert result == "hello\nworld"

    def test_preserves_tabs(self) -> None:
        """Tabs are preserved."""
        result = sanitize_prompt("hello\tworld")
        assert result == "hello\tworld"

    def test_empty_string(self) -> None:
        """Empty string returns empty."""
        result = sanitize_prompt("")
        assert result == ""


class TestValidateTaskId:
    """Tests for task ID validation."""

    def test_valid_uuid(self) -> None:
        """UUID format is valid."""
        result = validate_task_id("123e4567-e89b-12d3-a456-426614174000")
        assert result.valid

    def test_valid_alphanumeric(self) -> None:
        """Alphanumeric with hyphens is valid."""
        result = validate_task_id("task-123-abc")
        assert result.valid

    def test_valid_with_underscores(self) -> None:
        """Underscores are valid."""
        result = validate_task_id("task_123_abc")
        assert result.valid

    def test_empty_fails(self) -> None:
        """Empty ID fails."""
        result = validate_task_id("")
        assert not result.valid

    def test_too_long_fails(self) -> None:
        """ID exceeding max length fails."""
        result = validate_task_id("x" * 200)
        assert not result.valid

    def test_special_characters_fail(self) -> None:
        """Special characters fail."""
        result = validate_task_id("task@123")
        assert not result.valid

    def test_spaces_fail(self) -> None:
        """Spaces fail."""
        result = validate_task_id("task 123")
        assert not result.valid


class TestValidateContextId:
    """Tests for context ID validation."""

    def test_valid_id(self) -> None:
        """Valid context ID passes."""
        result = validate_context_id("context-123")
        assert result.valid

    def test_empty_fails(self) -> None:
        """Empty ID fails."""
        result = validate_context_id("")
        assert not result.valid

    def test_invalid_characters_fail(self) -> None:
        """Invalid characters fail."""
        result = validate_context_id("context/123")
        assert not result.valid


class TestValidateUrl:
    """Tests for URL validation."""

    def test_valid_https_url(self) -> None:
        """Valid HTTPS URL passes."""
        result = validate_url("https://example.com/path")
        assert result.valid

    def test_valid_http_url(self) -> None:
        """Valid HTTP URL passes."""
        result = validate_url("http://example.com")
        assert result.valid

    def test_invalid_scheme(self) -> None:
        """Non-HTTP schemes fail."""
        result = validate_url("ftp://example.com")
        assert not result.valid

    def test_localhost_blocked(self) -> None:
        """Localhost is blocked."""
        result = validate_url("http://localhost:8000")
        assert not result.valid

    def test_private_ip_blocked(self) -> None:
        """Private IPs are blocked."""
        result = validate_url("http://192.168.1.1")
        assert not result.valid

    def test_empty_fails(self) -> None:
        """Empty URL fails."""
        result = validate_url("")
        assert not result.valid


class TestValidateApiKey:
    """Tests for API key validation."""

    def test_valid_key(self) -> None:
        """Valid key passes."""
        result = validate_api_key("sk_1234567890abcdef")
        assert result.valid

    def test_too_short(self) -> None:
        """Key too short fails."""
        result = validate_api_key("short")
        assert not result.valid

    def test_too_long(self) -> None:
        """Key too long fails."""
        result = validate_api_key("x" * 300)
        assert not result.valid

    def test_invalid_characters(self) -> None:
        """Invalid characters fail."""
        result = validate_api_key("key with spaces 123")
        assert not result.valid

    def test_empty_fails(self) -> None:
        """Empty key fails."""
        result = validate_api_key("")
        assert not result.valid


class TestSanitizeHtml:
    """Tests for HTML sanitization."""

    def test_escapes_tags(self) -> None:
        """HTML tags are escaped."""
        result = sanitize_html("<script>alert('xss')</script>")
        assert "<" not in result
        assert ">" not in result

    def test_escapes_ampersand(self) -> None:
        """Ampersand is escaped."""
        result = sanitize_html("a & b")
        assert "&amp;" in result

    def test_escapes_quotes(self) -> None:
        """Quotes are escaped."""
        result = sanitize_html('say "hello"')
        assert "&quot;" in result


class TestInputValidator:
    """Tests for InputValidator class."""

    def test_validate_prompt(self) -> None:
        """Validates and sanitizes prompt."""
        validator = InputValidator()
        result = validator.validate_prompt("Hello\x00World")
        assert result == "HelloWorld"

    def test_validate_prompt_too_long(self) -> None:
        """Raises error for too long prompt."""
        validator = InputValidator(max_prompt_length=10)
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_prompt("This is too long")
        assert exc_info.value.field == "prompt"

    def test_validate_task_id(self) -> None:
        """Validates task ID."""
        validator = InputValidator()
        result = validator.validate_task_id("task-123")
        assert result == "task-123"

    def test_validate_task_id_invalid(self) -> None:
        """Raises error for invalid task ID."""
        validator = InputValidator()
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_task_id("task@123")
        assert exc_info.value.field == "task_id"

    def test_validate_context(self) -> None:
        """Validates context length."""
        validator = InputValidator(max_context_messages=5)
        context = [{"msg": i} for i in range(3)]
        result = validator.validate_context(context)
        assert len(result) == 3

    def test_validate_context_too_long(self) -> None:
        """Raises error for too long context."""
        validator = InputValidator(max_context_messages=2)
        context = [{"msg": i} for i in range(5)]
        with pytest.raises(ValidationError) as exc_info:
            validator.validate_context(context)
        assert exc_info.value.field == "context"
