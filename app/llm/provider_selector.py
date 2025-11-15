"""
LLM provider selection logic.

Sandi Metz Principles:
- Single Responsibility: Select optimal provider
- Small methods: Each method < 10 lines
- Clear naming: Self-documenting code
"""

from typing import List, Optional

from app.llm.circuit_breaker import CircuitBreaker, CircuitState
from app.llm.provider import BaseLLMProvider
from app.utils.logger import get_logger

logger = get_logger(__name__)


class ProviderSelectionStrategy:
    """Strategy for selecting LLM provider."""

    def select(
        self,
        providers: List[BaseLLMProvider],
        circuit_breakers: dict[str, CircuitBreaker],
        preferred_provider: Optional[str] = None,
    ) -> Optional[BaseLLMProvider]:
        """
        Select provider based on strategy.

        Args:
            providers: Available providers
            circuit_breakers: Circuit breakers by provider name
            preferred_provider: Optional preferred provider name

        Returns:
            Selected provider or None if none available
        """
        raise NotImplementedError


class PreferredProviderStrategy(ProviderSelectionStrategy):
    """Select preferred provider if available, fallback to first available."""

    def select(
        self,
        providers: List[BaseLLMProvider],
        circuit_breakers: dict[str, CircuitBreaker],
        preferred_provider: Optional[str] = None,
    ) -> Optional[BaseLLMProvider]:
        """Select preferred provider or first available."""
        if not providers:
            return None

        # Try preferred provider first
        if preferred_provider:
            for provider in providers:
                if self._is_available(provider, circuit_breakers):
                    if provider.get_name() == preferred_provider:
                        logger.info(
                            "Selected preferred provider", provider=preferred_provider
                        )
                        return provider

        # Fallback to first available
        for provider in providers:
            if self._is_available(provider, circuit_breakers):
                logger.info("Selected fallback provider", provider=provider.get_name())
                return provider

        logger.warning("No available providers")
        return None

    def _is_available(
        self,
        provider: BaseLLMProvider,
        circuit_breakers: dict[str, CircuitBreaker],
    ) -> bool:
        """
        Check if provider is available.

        Args:
            provider: Provider to check
            circuit_breakers: Circuit breakers by provider name

        Returns:
            True if provider's circuit is not OPEN
        """
        breaker = circuit_breakers.get(provider.get_name())
        if not breaker:
            return True

        return breaker.get_state() != CircuitState.OPEN


class RoundRobinStrategy(ProviderSelectionStrategy):
    """Round-robin selection among available providers."""

    def __init__(self):
        """Initialize round-robin strategy."""
        self._current_index = 0

    def select(
        self,
        providers: List[BaseLLMProvider],
        circuit_breakers: dict[str, CircuitBreaker],
        preferred_provider: Optional[str] = None,
    ) -> Optional[BaseLLMProvider]:
        """Select next available provider in round-robin fashion."""
        if not providers:
            return None

        available = [p for p in providers if self._is_available(p, circuit_breakers)]

        if not available:
            logger.warning("No available providers")
            return None

        # Round-robin through available providers
        provider = available[self._current_index % len(available)]
        self._current_index += 1

        logger.info("Selected provider (round-robin)", provider=provider.get_name())
        return provider

    def _is_available(
        self,
        provider: BaseLLMProvider,
        circuit_breakers: dict[str, CircuitBreaker],
    ) -> bool:
        """Check if provider is available."""
        breaker = circuit_breakers.get(provider.get_name())
        if not breaker:
            return True

        return breaker.get_state() != CircuitState.OPEN


class LLMProviderSelector:
    """
    Selector for choosing LLM providers.

    Uses configurable strategy to select optimal provider.
    """

    def __init__(self, strategy: Optional[ProviderSelectionStrategy] = None):
        """
        Initialize provider selector.

        Args:
            strategy: Selection strategy (default: PreferredProviderStrategy)
        """
        self._strategy = strategy or PreferredProviderStrategy()

    def select_provider(
        self,
        providers: List[BaseLLMProvider],
        circuit_breakers: dict[str, CircuitBreaker],
        preferred_provider: Optional[str] = None,
    ) -> Optional[BaseLLMProvider]:
        """
        Select optimal provider.

        Args:
            providers: Available providers
            circuit_breakers: Circuit breakers by provider name
            preferred_provider: Optional preferred provider name

        Returns:
            Selected provider or None if none available
        """
        return self._strategy.select(providers, circuit_breakers, preferred_provider)

    def set_strategy(self, strategy: ProviderSelectionStrategy) -> None:
        """
        Update selection strategy.

        Args:
            strategy: New selection strategy
        """
        self._strategy = strategy
        logger.info(
            "Updated provider selection strategy", strategy=type(strategy).__name__
        )
