"""Test cache entry models."""

from datetime import datetime, timedelta

from app.models.cache_entry import CacheEntry, SemanticMatch


class TestCacheEntry:
    """Test cache entry model."""

    def test_should_create_cache_entry(self):
        """Test basic cache entry creation."""
        entry = CacheEntry(
            query_hash="hash123",
            original_query="What is AI?",
            response="AI is artificial intelligence",
            provider="openai",
            model="gpt-3.5-turbo",
            prompt_tokens=10,
            completion_tokens=20,
        )

        assert entry.query_hash == "hash123"
        assert entry.original_query == "What is AI?"
        assert entry.response == "AI is artificial intelligence"
        assert entry.provider == "openai"
        assert entry.model == "gpt-3.5-turbo"
        assert entry.prompt_tokens == 10
        assert entry.completion_tokens == 20
        assert entry.hit_count == 0
        assert entry.embedding is None
        assert isinstance(entry.created_at, datetime)

    def test_should_create_with_embedding(self):
        """Test cache entry with embedding vector."""
        embedding = [0.1, 0.2, 0.3, 0.4, 0.5]
        entry = CacheEntry(
            query_hash="hash123",
            original_query="What is AI?",
            response="AI is artificial intelligence",
            provider="openai",
            model="gpt-3.5-turbo",
            prompt_tokens=10,
            completion_tokens=20,
            embedding=embedding,
        )

        assert entry.embedding == embedding
        assert len(entry.embedding) == 5

    def test_should_create_with_custom_hit_count(self):
        """Test cache entry with custom hit count."""
        entry = CacheEntry(
            query_hash="hash123",
            original_query="What is AI?",
            response="AI is artificial intelligence",
            provider="openai",
            model="gpt-3.5-turbo",
            prompt_tokens=10,
            completion_tokens=20,
            hit_count=5,
        )

        assert entry.hit_count == 5

    def test_should_calculate_total_tokens(self):
        """Test total tokens calculation."""
        entry = CacheEntry(
            query_hash="hash123",
            original_query="What is AI?",
            response="AI is artificial intelligence",
            provider="openai",
            model="gpt-3.5-turbo",
            prompt_tokens=15,
            completion_tokens=25,
        )

        assert entry.total_tokens == 40

    def test_should_calculate_age_seconds(self):
        """Test age calculation in seconds."""
        # Create entry with past timestamp
        past_time = datetime.utcnow() - timedelta(seconds=300)  # 5 minutes ago
        entry = CacheEntry(
            query_hash="hash123",
            original_query="What is AI?",
            response="AI is artificial intelligence",
            provider="openai",
            model="gpt-3.5-turbo",
            prompt_tokens=10,
            completion_tokens=20,
            created_at=past_time,
        )

        # Age should be approximately 300 seconds (allow small variation)
        assert 295 <= entry.age_seconds <= 305

    def test_should_calculate_age_for_new_entry(self):
        """Test age calculation for newly created entry."""
        entry = CacheEntry(
            query_hash="hash123",
            original_query="What is AI?",
            response="AI is artificial intelligence",
            provider="openai",
            model="gpt-3.5-turbo",
            prompt_tokens=10,
            completion_tokens=20,
        )

        # New entry should have age close to 0
        assert entry.age_seconds < 5

    def test_should_increment_hit_count(self):
        """Test hit count increment."""
        entry = CacheEntry(
            query_hash="hash123",
            original_query="What is AI?",
            response="AI is artificial intelligence",
            provider="openai",
            model="gpt-3.5-turbo",
            prompt_tokens=10,
            completion_tokens=20,
        )

        assert entry.hit_count == 0

        entry.increment_hit_count()
        assert entry.hit_count == 1

        entry.increment_hit_count()
        assert entry.hit_count == 2

        entry.increment_hit_count()
        assert entry.hit_count == 3

    def test_should_validate_non_negative_prompt_tokens(self):
        """Test validation of prompt tokens."""
        try:
            CacheEntry(
                query_hash="hash123",
                original_query="What is AI?",
                response="AI is artificial intelligence",
                provider="openai",
                model="gpt-3.5-turbo",
                prompt_tokens=-1,  # Invalid
                completion_tokens=20,
            )
            assert False, "Should have raised validation error"
        except ValueError:
            pass

    def test_should_validate_non_negative_completion_tokens(self):
        """Test validation of completion tokens."""
        try:
            CacheEntry(
                query_hash="hash123",
                original_query="What is AI?",
                response="AI is artificial intelligence",
                provider="openai",
                model="gpt-3.5-turbo",
                prompt_tokens=10,
                completion_tokens=-1,  # Invalid
            )
            assert False, "Should have raised validation error"
        except ValueError:
            pass

    def test_should_validate_non_negative_hit_count(self):
        """Test validation of hit count."""
        try:
            CacheEntry(
                query_hash="hash123",
                original_query="What is AI?",
                response="AI is artificial intelligence",
                provider="openai",
                model="gpt-3.5-turbo",
                prompt_tokens=10,
                completion_tokens=20,
                hit_count=-1,  # Invalid
            )
            assert False, "Should have raised validation error"
        except ValueError:
            pass

    def test_should_accept_zero_tokens(self):
        """Test that zero tokens are valid."""
        entry = CacheEntry(
            query_hash="hash123",
            original_query="What is AI?",
            response="AI is artificial intelligence",
            provider="openai",
            model="gpt-3.5-turbo",
            prompt_tokens=0,
            completion_tokens=0,
        )

        assert entry.total_tokens == 0

    def test_should_serialize_to_json(self):
        """Test serialization to JSON."""
        entry = CacheEntry(
            query_hash="hash123",
            original_query="What is AI?",
            response="AI is artificial intelligence",
            provider="openai",
            model="gpt-3.5-turbo",
            prompt_tokens=10,
            completion_tokens=20,
        )

        json_data = entry.model_dump()

        assert json_data["query_hash"] == "hash123"
        assert json_data["original_query"] == "What is AI?"
        assert json_data["provider"] == "openai"
        assert json_data["prompt_tokens"] == 10

    def test_should_deserialize_from_json(self):
        """Test deserialization from JSON."""
        data = {
            "query_hash": "hash123",
            "original_query": "What is AI?",
            "response": "AI is artificial intelligence",
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "created_at": "2025-11-12T10:30:00",
            "hit_count": 5,
        }

        entry = CacheEntry.model_validate(data)

        assert entry.query_hash == "hash123"
        assert entry.original_query == "What is AI?"
        assert entry.hit_count == 5

    def test_should_handle_large_embedding_vectors(self):
        """Test handling of high-dimensional embeddings."""
        # Create 384-dimensional embedding (common size)
        large_embedding = [0.1] * 384

        entry = CacheEntry(
            query_hash="hash123",
            original_query="What is AI?",
            response="AI is artificial intelligence",
            provider="openai",
            model="gpt-3.5-turbo",
            prompt_tokens=10,
            completion_tokens=20,
            embedding=large_embedding,
        )

        assert len(entry.embedding) == 384


class TestSemanticMatch:
    """Test semantic match model."""

    def test_should_create_semantic_match(self):
        """Test basic semantic match creation."""
        entry = CacheEntry(
            query_hash="hash123",
            original_query="What is AI?",
            response="AI is artificial intelligence",
            provider="openai",
            model="gpt-3.5-turbo",
            prompt_tokens=10,
            completion_tokens=20,
        )

        match = SemanticMatch(
            entry=entry,
            similarity_score=0.95,
            query_hash="hash456",
        )

        assert match.entry == entry
        assert match.similarity_score == 0.95
        assert match.query_hash == "hash456"

    def test_should_identify_strong_match(self):
        """Test strong match identification."""
        entry = CacheEntry(
            query_hash="hash123",
            original_query="What is AI?",
            response="AI is artificial intelligence",
            provider="openai",
            model="gpt-3.5-turbo",
            prompt_tokens=10,
            completion_tokens=20,
        )

        # Strong match (>= 0.90)
        strong = SemanticMatch(entry=entry, similarity_score=0.95, query_hash="hash456")
        assert strong.is_strong_match is True
        assert strong.is_moderate_match is False
        assert strong.is_weak_match is False

        # Exactly 0.90
        strong_edge = SemanticMatch(entry=entry, similarity_score=0.90, query_hash="hash456")
        assert strong_edge.is_strong_match is True

    def test_should_identify_moderate_match(self):
        """Test moderate match identification."""
        entry = CacheEntry(
            query_hash="hash123",
            original_query="What is AI?",
            response="AI is artificial intelligence",
            provider="openai",
            model="gpt-3.5-turbo",
            prompt_tokens=10,
            completion_tokens=20,
        )

        # Moderate match (0.80 - 0.89)
        moderate = SemanticMatch(entry=entry, similarity_score=0.85, query_hash="hash456")
        assert moderate.is_moderate_match is True
        assert moderate.is_strong_match is False
        assert moderate.is_weak_match is False

        # Lower edge (0.80)
        moderate_low = SemanticMatch(entry=entry, similarity_score=0.80, query_hash="hash456")
        assert moderate_low.is_moderate_match is True

        # Upper edge (0.89)
        moderate_high = SemanticMatch(entry=entry, similarity_score=0.89, query_hash="hash456")
        assert moderate_high.is_moderate_match is True

    def test_should_identify_weak_match(self):
        """Test weak match identification."""
        entry = CacheEntry(
            query_hash="hash123",
            original_query="What is AI?",
            response="AI is artificial intelligence",
            provider="openai",
            model="gpt-3.5-turbo",
            prompt_tokens=10,
            completion_tokens=20,
        )

        # Weak match (< 0.80)
        weak = SemanticMatch(entry=entry, similarity_score=0.75, query_hash="hash456")
        assert weak.is_weak_match is True
        assert weak.is_moderate_match is False
        assert weak.is_strong_match is False

        # Very weak
        very_weak = SemanticMatch(entry=entry, similarity_score=0.50, query_hash="hash456")
        assert very_weak.is_weak_match is True

    def test_should_validate_similarity_score_range(self):
        """Test similarity score validation."""
        entry = CacheEntry(
            query_hash="hash123",
            original_query="What is AI?",
            response="AI is artificial intelligence",
            provider="openai",
            model="gpt-3.5-turbo",
            prompt_tokens=10,
            completion_tokens=20,
        )

        # Valid range: 0.0 to 1.0
        valid_low = SemanticMatch(entry=entry, similarity_score=0.0, query_hash="hash456")
        assert valid_low.similarity_score == 0.0

        valid_high = SemanticMatch(entry=entry, similarity_score=1.0, query_hash="hash456")
        assert valid_high.similarity_score == 1.0

        # Invalid: below 0.0
        try:
            SemanticMatch(entry=entry, similarity_score=-0.1, query_hash="hash456")
            assert False, "Should have raised validation error"
        except ValueError:
            pass

        # Invalid: above 1.0
        try:
            SemanticMatch(entry=entry, similarity_score=1.1, query_hash="hash456")
            assert False, "Should have raised validation error"
        except ValueError:
            pass

    def test_should_access_entry_properties(self):
        """Test accessing entry properties through match."""
        entry = CacheEntry(
            query_hash="hash123",
            original_query="What is AI?",
            response="AI is artificial intelligence",
            provider="openai",
            model="gpt-3.5-turbo",
            prompt_tokens=10,
            completion_tokens=20,
        )

        match = SemanticMatch(entry=entry, similarity_score=0.95, query_hash="hash456")

        # Can access entry properties
        assert match.entry.query_hash == "hash123"
        assert match.entry.original_query == "What is AI?"
        assert match.entry.total_tokens == 30

    def test_should_serialize_to_json(self):
        """Test serialization to JSON."""
        entry = CacheEntry(
            query_hash="hash123",
            original_query="What is AI?",
            response="AI is artificial intelligence",
            provider="openai",
            model="gpt-3.5-turbo",
            prompt_tokens=10,
            completion_tokens=20,
        )

        match = SemanticMatch(entry=entry, similarity_score=0.95, query_hash="hash456")

        json_data = match.model_dump()

        assert json_data["similarity_score"] == 0.95
        assert json_data["query_hash"] == "hash456"
        assert "entry" in json_data

    def test_should_deserialize_from_json(self):
        """Test deserialization from JSON."""
        data = {
            "entry": {
                "query_hash": "hash123",
                "original_query": "What is AI?",
                "response": "AI is artificial intelligence",
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "prompt_tokens": 10,
                "completion_tokens": 20,
                "created_at": "2025-11-12T10:30:00",
                "hit_count": 0,
            },
            "similarity_score": 0.95,
            "query_hash": "hash456",
        }

        match = SemanticMatch.model_validate(data)

        assert match.similarity_score == 0.95
        assert match.query_hash == "hash456"
        assert match.entry.query_hash == "hash123"
