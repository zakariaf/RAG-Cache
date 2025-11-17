"""Test semantic matcher service."""

from unittest.mock import AsyncMock, Mock

import pytest

from app.models.embedding import EmbeddingResult
from app.models.qdrant_point import SearchResult
from app.services.semantic_matcher import (
    SemanticMatch,
    SemanticMatcher,
    SemanticMatchError,
)


@pytest.fixture
def mock_embedding_generator():
    """Create mock embedding generator."""
    generator = Mock()
    generator.generate = AsyncMock()
    generator.get_embedding_dimensions = Mock(return_value=384)
    generator.health_check = AsyncMock(return_value=True)
    return generator


@pytest.fixture
def mock_qdrant_repository():
    """Create mock Qdrant repository."""
    repo = Mock()
    repo.search_similar = AsyncMock()
    repo.store_point = AsyncMock(return_value=True)
    repo.delete_point = AsyncMock()
    repo.ping = AsyncMock(return_value=True)
    return repo


@pytest.fixture
def sample_embedding():
    """Create sample embedding result."""
    return EmbeddingResult.create(
        text="test query",
        vector=[0.1, 0.2, 0.3],
        model="test-model",
        tokens=2,
    )


@pytest.fixture
def sample_search_result():
    """Create sample search result."""
    return SearchResult(
        point_id="test-id",
        score=0.95,
        payload={
            "query": "similar query",
            "response": "cached response",
        },
    )


@pytest.fixture
def matcher(mock_embedding_generator, mock_qdrant_repository):
    """Create semantic matcher."""
    return SemanticMatcher(
        embedding_generator=mock_embedding_generator,
        qdrant_repository=mock_qdrant_repository,
        similarity_threshold=0.8,
        max_results=5,
    )


class TestSemanticMatch:
    """Test SemanticMatch class."""

    def test_initialization(self):
        """Test semantic match initialization."""
        match = SemanticMatch(
            query="test query",
            score=0.95,
            cached_response="response",
            metadata={"key": "value"},
        )

        assert match.query == "test query"
        assert match.score == 0.95
        assert match.cached_response == "response"
        assert match.metadata["key"] == "value"

    def test_initialization_defaults(self):
        """Test initialization with defaults."""
        match = SemanticMatch(query="test", score=0.9)

        assert match.cached_response is None
        assert match.metadata == {}

    def test_repr(self):
        """Test string representation."""
        match = SemanticMatch(query="test query", score=0.95)

        repr_str = repr(match)

        assert "SemanticMatch" in repr_str
        assert "0.95" in repr_str

    def test_to_dict(self):
        """Test converting to dictionary."""
        match = SemanticMatch(
            query="test",
            score=0.95,
            cached_response="response",
            metadata={"key": "value"},
        )

        match_dict = match.to_dict()

        assert match_dict["query"] == "test"
        assert match_dict["score"] == 0.95
        assert match_dict["cached_response"] == "response"
        assert match_dict["metadata"]["key"] == "value"


class TestSemanticMatcher:
    """Test SemanticMatcher class."""

    @pytest.mark.asyncio
    async def test_find_matches(
        self,
        matcher,
        mock_embedding_generator,
        mock_qdrant_repository,
        sample_embedding,
        sample_search_result,
    ):
        """Test finding semantic matches."""
        mock_embedding_generator.generate.return_value = sample_embedding
        mock_qdrant_repository.search_similar.return_value = [sample_search_result]

        matches = await matcher.find_matches("test query")

        assert len(matches) == 1
        assert matches[0].query == "similar query"
        assert matches[0].score == 0.95
        assert matches[0].cached_response == "cached response"

    @pytest.mark.asyncio
    async def test_find_matches_custom_threshold(
        self,
        matcher,
        mock_embedding_generator,
        mock_qdrant_repository,
        sample_embedding,
    ):
        """Test finding matches with custom threshold."""
        mock_embedding_generator.generate.return_value = sample_embedding
        mock_qdrant_repository.search_similar.return_value = []

        await matcher.find_matches("test query", threshold=0.95)

        # Verify search was called with custom threshold
        call_kwargs = mock_qdrant_repository.search_similar.call_args[1]
        assert call_kwargs["score_threshold"] == 0.95

    @pytest.mark.asyncio
    async def test_find_matches_custom_limit(
        self,
        matcher,
        mock_embedding_generator,
        mock_qdrant_repository,
        sample_embedding,
    ):
        """Test finding matches with custom limit."""
        mock_embedding_generator.generate.return_value = sample_embedding
        mock_qdrant_repository.search_similar.return_value = []

        await matcher.find_matches("test query", limit=10)

        # Verify search was called with custom limit
        call_kwargs = mock_qdrant_repository.search_similar.call_args[1]
        assert call_kwargs["limit"] == 10

    @pytest.mark.asyncio
    async def test_find_matches_empty_results(
        self,
        matcher,
        mock_embedding_generator,
        mock_qdrant_repository,
        sample_embedding,
    ):
        """Test finding matches with no results."""
        mock_embedding_generator.generate.return_value = sample_embedding
        mock_qdrant_repository.search_similar.return_value = []

        matches = await matcher.find_matches("test query")

        assert len(matches) == 0

    @pytest.mark.asyncio
    async def test_find_matches_sorted_by_score(
        self,
        matcher,
        mock_embedding_generator,
        mock_qdrant_repository,
        sample_embedding,
    ):
        """Test matches are sorted by score descending."""
        mock_embedding_generator.generate.return_value = sample_embedding
        mock_qdrant_repository.search_similar.return_value = [
            SearchResult("id1", 0.7, {"query": "q1"}),
            SearchResult("id2", 0.9, {"query": "q2"}),
            SearchResult("id3", 0.8, {"query": "q3"}),
        ]

        matches = await matcher.find_matches("test query")

        assert matches[0].score == 0.9
        assert matches[1].score == 0.8
        assert matches[2].score == 0.7

    @pytest.mark.asyncio
    async def test_find_matches_error_handling(
        self,
        matcher,
        mock_embedding_generator,
    ):
        """Test error handling when finding matches."""
        mock_embedding_generator.generate.side_effect = Exception("Generation failed")

        with pytest.raises(SemanticMatchError, match="Failed to find semantic matches"):
            await matcher.find_matches("test query")

    @pytest.mark.asyncio
    async def test_find_best_match(
        self,
        matcher,
        mock_embedding_generator,
        mock_qdrant_repository,
        sample_embedding,
        sample_search_result,
    ):
        """Test finding best match."""
        mock_embedding_generator.generate.return_value = sample_embedding
        mock_qdrant_repository.search_similar.return_value = [sample_search_result]

        match = await matcher.find_best_match("test query")

        assert match is not None
        assert match.score == 0.95

    @pytest.mark.asyncio
    async def test_find_best_match_none(
        self,
        matcher,
        mock_embedding_generator,
        mock_qdrant_repository,
        sample_embedding,
    ):
        """Test best match returns None when no matches."""
        mock_embedding_generator.generate.return_value = sample_embedding
        mock_qdrant_repository.search_similar.return_value = []

        match = await matcher.find_best_match("test query")

        assert match is None

    @pytest.mark.asyncio
    async def test_has_semantic_match_true(
        self,
        matcher,
        mock_embedding_generator,
        mock_qdrant_repository,
        sample_embedding,
        sample_search_result,
    ):
        """Test has_semantic_match returns True."""
        mock_embedding_generator.generate.return_value = sample_embedding
        mock_qdrant_repository.search_similar.return_value = [sample_search_result]

        has_match = await matcher.has_semantic_match("test query")

        assert has_match is True

    @pytest.mark.asyncio
    async def test_has_semantic_match_false(
        self,
        matcher,
        mock_embedding_generator,
        mock_qdrant_repository,
        sample_embedding,
    ):
        """Test has_semantic_match returns False."""
        mock_embedding_generator.generate.return_value = sample_embedding
        mock_qdrant_repository.search_similar.return_value = []

        has_match = await matcher.has_semantic_match("test query")

        assert has_match is False

    @pytest.mark.asyncio
    async def test_has_semantic_match_error_returns_false(
        self,
        matcher,
        mock_embedding_generator,
    ):
        """Test has_semantic_match returns False on error."""
        mock_embedding_generator.generate.side_effect = Exception("Failed")

        has_match = await matcher.has_semantic_match("test query")

        assert has_match is False

    @pytest.mark.asyncio
    async def test_store_query_embedding(
        self,
        matcher,
        mock_embedding_generator,
        mock_qdrant_repository,
        sample_embedding,
    ):
        """Test storing query embedding."""
        mock_embedding_generator.generate.return_value = sample_embedding
        mock_qdrant_repository.store_point.return_value = True

        success = await matcher.store_query_embedding(
            query="test query",
            response="test response",
            point_id="test-id",
            metadata={"key": "value"},
        )

        assert success is True
        mock_qdrant_repository.store_point.assert_called_once()

    @pytest.mark.asyncio
    async def test_store_query_embedding_with_metadata(
        self,
        matcher,
        mock_embedding_generator,
        mock_qdrant_repository,
        sample_embedding,
    ):
        """Test storing embedding with metadata."""
        mock_embedding_generator.generate.return_value = sample_embedding
        mock_qdrant_repository.store_point.return_value = True

        await matcher.store_query_embedding(
            query="test",
            response="response",
            point_id="id",
            metadata={"custom": "data"},
        )

        # Verify point was created with metadata
        call_args = mock_qdrant_repository.store_point.call_args[0]
        point = call_args[0]
        assert point.payload["custom"] == "data"

    @pytest.mark.asyncio
    async def test_store_query_embedding_error(
        self,
        matcher,
        mock_embedding_generator,
    ):
        """Test error handling when storing embedding."""
        mock_embedding_generator.generate.side_effect = Exception("Failed")

        with pytest.raises(SemanticMatchError, match="Failed to store query embedding"):
            await matcher.store_query_embedding(
                query="test",
                response="response",
                point_id="id",
            )

    @pytest.mark.asyncio
    async def test_delete_query_embedding(
        self,
        matcher,
        mock_qdrant_repository,
    ):
        """Test deleting query embedding."""
        delete_result = Mock()
        delete_result.success = True
        mock_qdrant_repository.delete_point.return_value = delete_result

        success = await matcher.delete_query_embedding("test-id")

        assert success is True
        mock_qdrant_repository.delete_point.assert_called_once_with("test-id")

    @pytest.mark.asyncio
    async def test_delete_query_embedding_failed(
        self,
        matcher,
        mock_qdrant_repository,
    ):
        """Test delete returns False on failure."""
        delete_result = Mock()
        delete_result.success = False
        mock_qdrant_repository.delete_point.return_value = delete_result

        success = await matcher.delete_query_embedding("test-id")

        assert success is False

    @pytest.mark.asyncio
    async def test_delete_query_embedding_error(
        self,
        matcher,
        mock_qdrant_repository,
    ):
        """Test delete returns False on exception."""
        mock_qdrant_repository.delete_point.side_effect = Exception("Failed")

        success = await matcher.delete_query_embedding("test-id")

        assert success is False

    def test_set_threshold(self, matcher):
        """Test setting similarity threshold."""
        matcher.set_threshold(0.9)

        assert matcher._similarity_threshold == 0.9

    def test_set_threshold_invalid(self, matcher):
        """Test setting invalid threshold raises error."""
        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            matcher.set_threshold(1.5)

        with pytest.raises(ValueError, match="between 0.0 and 1.0"):
            matcher.set_threshold(-0.1)

    def test_set_max_results(self, matcher):
        """Test setting max results."""
        matcher.set_max_results(10)

        assert matcher._max_results == 10

    def test_set_max_results_invalid(self, matcher):
        """Test setting invalid max results raises error."""
        with pytest.raises(ValueError, match="must be positive"):
            matcher.set_max_results(0)

    def test_get_config(self, matcher, mock_embedding_generator):
        """Test getting matcher configuration."""
        config = matcher.get_config()

        assert config["similarity_threshold"] == 0.8
        assert config["max_results"] == 5
        assert config["vector_dimensions"] == 384

    @pytest.mark.asyncio
    async def test_health_check_success(
        self,
        matcher,
        mock_embedding_generator,
        mock_qdrant_repository,
    ):
        """Test health check when all healthy."""
        mock_embedding_generator.health_check.return_value = True
        mock_qdrant_repository.ping.return_value = True

        is_healthy = await matcher.health_check()

        assert is_healthy is True

    @pytest.mark.asyncio
    async def test_health_check_generator_unhealthy(
        self,
        matcher,
        mock_embedding_generator,
        mock_qdrant_repository,
    ):
        """Test health check fails when generator unhealthy."""
        mock_embedding_generator.health_check.return_value = False
        mock_qdrant_repository.ping.return_value = True

        is_healthy = await matcher.health_check()

        assert is_healthy is False

    @pytest.mark.asyncio
    async def test_health_check_qdrant_unhealthy(
        self,
        matcher,
        mock_embedding_generator,
        mock_qdrant_repository,
    ):
        """Test health check fails when Qdrant unhealthy."""
        mock_embedding_generator.health_check.return_value = True
        mock_qdrant_repository.ping.return_value = False

        is_healthy = await matcher.health_check()

        assert is_healthy is False

    @pytest.mark.asyncio
    async def test_health_check_error(
        self,
        matcher,
        mock_embedding_generator,
    ):
        """Test health check returns False on error."""
        mock_embedding_generator.health_check.side_effect = Exception("Failed")

        is_healthy = await matcher.health_check()

        assert is_healthy is False


class TestSemanticMatcherIntegration:
    """Test semantic matcher integration scenarios."""

    @pytest.mark.asyncio
    async def test_full_match_workflow(
        self,
        matcher,
        mock_embedding_generator,
        mock_qdrant_repository,
        sample_embedding,
    ):
        """Test complete workflow: store then find."""
        mock_embedding_generator.generate.return_value = sample_embedding
        mock_qdrant_repository.store_point.return_value = True

        # Store query
        await matcher.store_query_embedding(
            query="test query",
            response="test response",
            point_id="id1",
        )

        # Set up search result
        search_result = SearchResult(
            point_id="id1",
            score=0.95,
            payload={"query": "test query", "response": "test response"},
        )
        mock_qdrant_repository.search_similar.return_value = [search_result]

        # Find match
        match = await matcher.find_best_match("similar query")

        assert match is not None
        assert match.cached_response == "test response"
