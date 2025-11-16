"""
Mock LLM providers for testing.

Sandi Metz Principles:
- Single Responsibility: Provide test doubles
- Small classes: Each mock < 100 lines
- Clear naming: Self-documenting code
"""

from typing import Optional

from app.llm.provider import BaseLLMProvider
from app.models.llm import LLMResponse
from app.models.query import QueryRequest


class MockLLMProvider(BaseLLMProvider):
    """
    Mock LLM provider for testing.

    Returns configurable responses without making real API calls.
    """

    def __init__(
        self,
        name: str = "mock-provider",
        response_content: str = "mock response",
        prompt_tokens: int = 10,
        completion_tokens: int = 5,
        model: str = "mock-model",
        should_fail: bool = False,
        failure_message: str = "Mock provider error",
    ):
        """
        Initialize mock provider.

        Args:
            name: Provider name
            response_content: Content to return in responses
            prompt_tokens: Mock prompt token count
            completion_tokens: Mock completion token count
            model: Model name to return
            should_fail: Whether to raise exceptions
            failure_message: Error message when failing
        """
        self._name = name
        self._response_content = response_content
        self._prompt_tokens = prompt_tokens
        self._completion_tokens = completion_tokens
        self._model = model
        self._should_fail = should_fail
        self._failure_message = failure_message
        self._call_count = 0

    async def complete(self, request: QueryRequest) -> LLMResponse:
        """
        Return mock response.

        Args:
            request: Query request

        Returns:
            Mock LLM response

        Raises:
            Exception: If should_fail is True
        """
        self._call_count += 1

        if self._should_fail:
            raise Exception(self._failure_message)

        return LLMResponse(
            content=self._response_content,
            prompt_tokens=self._prompt_tokens,
            completion_tokens=self._completion_tokens,
            model=self._model,
        )

    def get_name(self) -> str:
        """Get provider name."""
        return self._name

    def get_call_count(self) -> int:
        """
        Get number of times complete was called.

        Returns:
            Call count
        """
        return self._call_count

    def reset_call_count(self) -> None:
        """Reset call counter."""
        self._call_count = 0

    def set_should_fail(self, should_fail: bool) -> None:
        """
        Configure whether provider should fail.

        Args:
            should_fail: True to raise exceptions
        """
        self._should_fail = should_fail

    def set_response_content(self, content: str) -> None:
        """
        Set response content.

        Args:
            content: New response content
        """
        self._response_content = content


class MockOpenAIProvider(BaseLLMProvider):
    """Mock OpenAI provider."""

    def __init__(self, should_fail: bool = False):
        """
        Initialize mock OpenAI provider.

        Args:
            should_fail: Whether to fail on complete
        """
        self._should_fail = should_fail
        self._call_count = 0

    async def complete(self, request: QueryRequest) -> LLMResponse:
        """Return mock OpenAI response."""
        self._call_count += 1

        if self._should_fail:
            raise Exception("OpenAI API error")

        return LLMResponse(
            content="Mock OpenAI response",
            prompt_tokens=50,
            completion_tokens=25,
            model="gpt-3.5-turbo",
        )

    def get_name(self) -> str:
        """Get provider name."""
        return "openai"

    def get_call_count(self) -> int:
        """Get call count."""
        return self._call_count


class MockAnthropicProvider(BaseLLMProvider):
    """Mock Anthropic provider."""

    def __init__(self, should_fail: bool = False):
        """
        Initialize mock Anthropic provider.

        Args:
            should_fail: Whether to fail on complete
        """
        self._should_fail = should_fail
        self._call_count = 0

    async def complete(self, request: QueryRequest) -> LLMResponse:
        """Return mock Anthropic response."""
        self._call_count += 1

        if self._should_fail:
            raise Exception("Anthropic API error")

        return LLMResponse(
            content="Mock Claude response",
            prompt_tokens=60,
            completion_tokens=30,
            model="claude-3-sonnet-20240229",
        )

    def get_name(self) -> str:
        """Get provider name."""
        return "anthropic"

    def get_call_count(self) -> int:
        """Get call count."""
        return self._call_count


class FailingMockProvider(BaseLLMProvider):
    """Mock provider that always fails."""

    def __init__(
        self,
        name: str = "failing-provider",
        error_message: str = "Mock error",
    ):
        """
        Initialize failing mock provider.

        Args:
            name: Provider name
            error_message: Error message to raise
        """
        self._name = name
        self._error_message = error_message
        self._call_count = 0

    async def complete(self, request: QueryRequest) -> LLMResponse:
        """Always raise exception."""
        self._call_count += 1
        raise Exception(self._error_message)

    def get_name(self) -> str:
        """Get provider name."""
        return self._name

    def get_call_count(self) -> int:
        """Get call count."""
        return self._call_count


class CountingMockProvider(BaseLLMProvider):
    """Mock provider that tracks detailed call information."""

    def __init__(self, name: str = "counting-provider"):
        """
        Initialize counting mock provider.

        Args:
            name: Provider name
        """
        self._name = name
        self._calls: list[QueryRequest] = []

    async def complete(self, request: QueryRequest) -> LLMResponse:
        """Track call and return mock response."""
        self._calls.append(request)

        return LLMResponse(
            content=f"Response #{len(self._calls)}",
            prompt_tokens=10,
            completion_tokens=5,
            model="counting-model",
        )

    def get_name(self) -> str:
        """Get provider name."""
        return self._name

    def get_call_count(self) -> int:
        """Get number of calls."""
        return len(self._calls)

    def get_last_request(self) -> Optional[QueryRequest]:
        """
        Get last request received.

        Returns:
            Last query request or None if no calls
        """
        return self._calls[-1] if self._calls else None

    def get_all_requests(self) -> list[QueryRequest]:
        """
        Get all requests received.

        Returns:
            List of all query requests
        """
        return self._calls.copy()

    def reset(self) -> None:
        """Reset all tracking data."""
        self._calls.clear()
