"""Unit tests for Semantic Matcher Service."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.exceptions import SemanticMatchError
from app.models.qdrant_point import SearchResult
from app.pipeline.semantic_matcher import SemanticMatch, SemanticMatcher
from app.similarity.score_calculator import SimilarityLevel


class TestSemanticMatch:
    """Tests for SemanticMatch dataclass."""

    def test_is_high_quality_exact(self):
        """Test high quality detection for exact match."""
        match = SemanticMatch(
            query_hash="hash1",
            original_query="test query",
            cached_response="response",
            similarity_score=0.98,
            similarity_level=SimilarityLevel.EXACT,
            provider="openai",
            model="gpt-4",
            point_id="point1",
        )
        assert match.is_high_quality is True

    def test_is_high_quality_low(self):
        """Test high quality detection for low match."""
        match = SemanticMatch(
            query_hash="hash1",
            original_query="test query",
            cached_response="response",
            similarity_score=0.5,
            similarity_level=SimilarityLevel.LOW,
            provider="openai",
            model="gpt-4",
            point_id="point1",
        )
        assert match.is_high_quality is False

    def test_confidence_property(self):
        """Test confidence description."""
        match = SemanticMatch(
            query_hash="hash1",
            original_query="test query",
            cached_response="response",
            similarity_score=0.92,
            similarity_level=SimilarityLevel.VERY_HIGH,
            provider="openai",
            model="gpt-4",
            point_id="point1",
        )
        assert "confidence" in match.confidence.lower()


class TestSemanticMatcher:
    """Tests for SemanticMatcher class."""

    @pytest.fixture
    def mock_embedding_generator(self):
        """Create mock embedding generator."""
        mock = MagicMock()
        mock.generate = AsyncMock(return_value=[0.1] * 384)
        return mock

    @pytest.fixture
    def mock_qdrant_repository(self):
        """Create mock Qdrant repository."""
        mock = MagicMock()
        mock.search_similar = AsyncMock(return_value=[])
        mock.store_point = AsyncMock(return_value=True)
        mock.ping = AsyncMock(return_value=True)
        return mock

    @pytest.fixture
    def matcher(self, mock_embedding_generator, mock_qdrant_repository):
        """Create semantic matcher with mocks."""
        return SemanticMatcher(
            embedding_generator=mock_embedding_generator,
            qdrant_repository=mock_qdrant_repository,
            similarity_threshold=0.85,
        )

    @pytest.mark.asyncio
    async def test_find_match_no_results(self, matcher, mock_qdrant_repository):
        """Test find_match returns None when no results."""
        mock_qdrant_repository.search_similar = AsyncMock(return_value=[])
        result = await matcher.find_match("test query")
        assert result is None

    @pytest.mark.asyncio
    async def test_find_match_with_result(
        self, matcher, mock_embedding_generator, mock_qdrant_repository
    ):
        """Test find_match returns match when found."""
        search_result = SearchResult(
            point_id="point1",
            score=0.95,
            vector=None,
            payload={
                "query_hash": "hash1",
                "original_query": "similar query",
                "response": "cached response",
                "provider": "openai",
                "model": "gpt-4",
            },
        )
        mock_qdrant_repository.search_similar = AsyncMock(return_value=[search_result])

        result = await matcher.find_match("test query")

        assert result is not None
        assert result.similarity_score == 0.95
        assert result.cached_response == "cached response"
        mock_embedding_generator.generate.assert_called_once_with("test query")

    @pytest.mark.asyncio
    async def test_find_matches_multiple(self, matcher, mock_qdrant_repository):
        """Test find_matches returns multiple results."""
        search_results = [
            SearchResult(
                point_id=f"point{i}",
                score=0.9 - i * 0.05,
                vector=None,
                payload={
                    "query_hash": f"hash{i}",
                    "original_query": f"query {i}",
                    "response": f"response {i}",
                    "provider": "openai",
                    "model": "gpt-4",
                },
            )
            for i in range(3)
        ]
        mock_qdrant_repository.search_similar = AsyncMock(return_value=search_results)

        results = await matcher.find_matches("test query", limit=3)

        assert len(results) == 3
        assert results[0].similarity_score == 0.9

    @pytest.mark.asyncio
    async def test_store_for_matching(
        self, mock_embedding_generator, mock_qdrant_repository
    ):
        """Test store_for_matching stores query."""
        # Create matcher fresh for this test
        matcher = SemanticMatcher(
            embedding_generator=mock_embedding_generator,
            qdrant_repository=mock_qdrant_repository,
            similarity_threshold=0.85,
        )

        result = await matcher.store_for_matching(
            query="test query",
            query_hash="hash1",
            response="test response",
            provider="openai",
            model="gpt-4",
        )

        assert result is True
        mock_embedding_generator.generate.assert_called_once_with("test query")
        mock_qdrant_repository.store_point.assert_called_once()

        # Verify the point was created with correct payload
        call_args = mock_qdrant_repository.store_point.call_args
        point = call_args[0][0]  # First positional arg
        assert point.payload["query_hash"] == "hash1"
        assert point.payload["original_query"] == "test query"
        assert point.payload["response"] == "test response"
        assert point.payload["provider"] == "openai"
        assert point.payload["model"] == "gpt-4"

    @pytest.mark.asyncio
    async def test_store_for_matching_failure(self, matcher, mock_qdrant_repository):
        """Test store_for_matching handles failure."""
        mock_qdrant_repository.store_point = AsyncMock(return_value=False)

        result = await matcher.store_for_matching(
            query="test query",
            query_hash="hash1",
            response="test response",
            provider="openai",
            model="gpt-4",
        )

        assert result is False

    @pytest.mark.asyncio
    async def test_is_healthy(self, matcher, mock_qdrant_repository):
        """Test health check."""
        mock_qdrant_repository.ping = AsyncMock(return_value=True)
        result = await matcher.is_healthy()
        assert result is True

    def test_threshold_property(self, matcher):
        """Test threshold getter."""
        assert matcher.threshold == 0.85

    def test_set_threshold_valid(self, matcher):
        """Test threshold setter with valid value."""
        matcher.set_threshold(0.9)
        assert matcher.threshold == 0.9

    def test_set_threshold_invalid(self, matcher):
        """Test threshold setter with invalid value."""
        with pytest.raises(ValueError):
            matcher.set_threshold(1.5)

    @pytest.mark.asyncio
    async def test_find_match_error_handling(self, matcher, mock_embedding_generator):
        """Test find_match error handling."""
        mock_embedding_generator.generate = AsyncMock(
            side_effect=Exception("Embedding error")
        )

        with pytest.raises(SemanticMatchError):
            await matcher.find_match("test query")
