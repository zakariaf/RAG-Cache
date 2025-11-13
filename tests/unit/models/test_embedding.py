"""Test embedding vector models."""

import pytest

from app.models.embedding import EmbeddingResult, EmbeddingVector


class TestEmbeddingVector:
    """Test embedding vector model."""

    def test_should_create_embedding_vector(self):
        """Test basic embedding creation."""
        vector = EmbeddingVector(
            vector=[0.1, 0.2, 0.3],
            dimensions=3,
            model="test-model",
            normalized=False,
        )

        assert vector.vector == [0.1, 0.2, 0.3]
        assert vector.dimensions == 3
        assert vector.model == "test-model"
        assert vector.normalized is False

    def test_should_create_with_factory_method(self):
        """Test factory method creation."""
        vector = EmbeddingVector.create(
            vector=[1.0, 2.0, 3.0],
            model="sentence-transformers/all-MiniLM-L6-v2",
        )

        assert vector.dimensions == 3
        assert vector.model == "sentence-transformers/all-MiniLM-L6-v2"
        assert vector.normalized is False

    def test_should_auto_detect_dimensions(self):
        """Test automatic dimension detection."""
        vector = EmbeddingVector.create(
            vector=[0.1, 0.2, 0.3, 0.4, 0.5],
            model="test-model",
        )

        assert vector.dimensions == 5

    def test_should_validate_empty_vector(self):
        """Test validation of empty vector."""
        with pytest.raises(ValueError, match="Embedding vector cannot be empty"):
            EmbeddingVector.create(vector=[], model="test-model")

    def test_should_validate_empty_model(self):
        """Test validation of empty model name."""
        with pytest.raises(ValueError, match="Model name cannot be empty"):
            EmbeddingVector.create(vector=[1.0, 2.0], model="")

    def test_should_validate_nan_values(self):
        """Test validation of NaN values."""
        with pytest.raises(ValueError, match="Vector contains NaN or Inf"):
            EmbeddingVector.create(vector=[1.0, float("nan"), 3.0], model="test-model")

    def test_should_validate_inf_values(self):
        """Test validation of infinite values."""
        with pytest.raises(ValueError, match="Vector contains NaN or Inf"):
            EmbeddingVector.create(vector=[1.0, float("inf"), 3.0], model="test-model")

    def test_should_calculate_magnitude(self):
        """Test magnitude calculation."""
        vector = EmbeddingVector.create(vector=[3.0, 4.0], model="test-model")

        # sqrt(3^2 + 4^2) = sqrt(9 + 16) = sqrt(25) = 5
        assert vector.magnitude == 5.0

    def test_should_normalize_vector(self):
        """Test vector normalization."""
        vector = EmbeddingVector.create(vector=[3.0, 4.0], model="test-model")
        normalized = vector.normalize()

        # Should be unit vector
        assert normalized.is_unit_vector
        assert normalized.normalized is True
        # Original should be unchanged
        assert vector.normalized is False

        # Check normalized values
        assert abs(normalized.vector[0] - 0.6) < 1e-10  # 3/5
        assert abs(normalized.vector[1] - 0.8) < 1e-10  # 4/5

    def test_should_reject_normalizing_zero_vector(self):
        """Test that zero vector cannot be normalized."""
        vector = EmbeddingVector.create(vector=[0.0, 0.0, 0.0], model="test-model")

        with pytest.raises(ValueError, match="Cannot normalize zero vector"):
            vector.normalize()

    def test_should_identify_zero_vector(self):
        """Test zero vector identification."""
        zero_vector = EmbeddingVector.create(vector=[0.0, 0.0, 0.0], model="test-model")
        non_zero = EmbeddingVector.create(vector=[1.0, 0.0, 0.0], model="test-model")

        assert zero_vector.is_zero_vector is True
        assert non_zero.is_zero_vector is False

    def test_should_identify_unit_vector(self):
        """Test unit vector identification."""
        # Create normalized vector
        vector = EmbeddingVector.create(vector=[3.0, 4.0], model="test-model")
        unit_vector = vector.normalize()

        assert unit_vector.is_unit_vector is True
        assert vector.is_unit_vector is False

    def test_should_calculate_dot_product(self):
        """Test dot product calculation."""
        v1 = EmbeddingVector.create(vector=[1.0, 2.0, 3.0], model="test-model")
        v2 = EmbeddingVector.create(vector=[4.0, 5.0, 6.0], model="test-model")

        # 1*4 + 2*5 + 3*6 = 4 + 10 + 18 = 32
        dot_prod = v1.dot_product(v2)

        assert dot_prod == 32.0

    def test_should_reject_dot_product_dimension_mismatch(self):
        """Test dot product with mismatched dimensions."""
        v1 = EmbeddingVector.create(vector=[1.0, 2.0], model="test-model")
        v2 = EmbeddingVector.create(vector=[1.0, 2.0, 3.0], model="test-model")

        with pytest.raises(ValueError, match="Dimension mismatch"):
            v1.dot_product(v2)

    def test_should_calculate_cosine_similarity(self):
        """Test cosine similarity calculation."""
        v1 = EmbeddingVector.create(vector=[1.0, 0.0, 0.0], model="test-model")
        v2 = EmbeddingVector.create(vector=[1.0, 0.0, 0.0], model="test-model")

        # Same vector should have similarity of 1.0
        similarity = v1.cosine_similarity(v2)
        assert abs(similarity - 1.0) < 1e-10

    def test_should_calculate_cosine_similarity_orthogonal(self):
        """Test cosine similarity of orthogonal vectors."""
        v1 = EmbeddingVector.create(vector=[1.0, 0.0, 0.0], model="test-model")
        v2 = EmbeddingVector.create(vector=[0.0, 1.0, 0.0], model="test-model")

        # Orthogonal vectors should have similarity of 0.0
        similarity = v1.cosine_similarity(v2)
        assert abs(similarity) < 1e-10

    def test_should_calculate_cosine_similarity_normalized(self):
        """Test cosine similarity with normalized vectors."""
        v1 = EmbeddingVector.create(vector=[3.0, 4.0], model="test-model").normalize()
        v2 = EmbeddingVector.create(vector=[3.0, 4.0], model="test-model").normalize()

        # Should use fast path (dot product only)
        similarity = v1.cosine_similarity(v2)
        assert abs(similarity - 1.0) < 1e-10

    def test_should_reject_cosine_similarity_dimension_mismatch(self):
        """Test cosine similarity with mismatched dimensions."""
        v1 = EmbeddingVector.create(vector=[1.0, 2.0], model="test-model")
        v2 = EmbeddingVector.create(vector=[1.0, 2.0, 3.0], model="test-model")

        with pytest.raises(ValueError, match="Dimension mismatch"):
            v1.cosine_similarity(v2)

    def test_should_reject_cosine_similarity_zero_vector(self):
        """Test cosine similarity with zero vector."""
        v1 = EmbeddingVector.create(vector=[0.0, 0.0], model="test-model")
        v2 = EmbeddingVector.create(vector=[1.0, 2.0], model="test-model")

        with pytest.raises(
            ValueError, match="Cannot calculate cosine similarity with zero vector"
        ):
            v1.cosine_similarity(v2)

    def test_should_convert_to_list(self):
        """Test conversion to list."""
        original = [1.0, 2.0, 3.0]
        vector = EmbeddingVector.create(vector=original, model="test-model")

        result = vector.to_list()

        assert result == original
        # Should be a copy
        assert result is not vector.vector

    def test_should_handle_large_dimensions(self):
        """Test handling of high-dimensional vectors."""
        # Create 384-dimensional vector (common for sentence transformers)
        large_vector = [0.1] * 384
        vector = EmbeddingVector.create(vector=large_vector, model="test-model")

        assert vector.dimensions == 384
        assert len(vector.vector) == 384

    def test_should_serialize_to_json(self):
        """Test serialization."""
        vector = EmbeddingVector.create(vector=[1.0, 2.0, 3.0], model="test-model")

        json_data = vector.model_dump()

        assert json_data["vector"] == [1.0, 2.0, 3.0]
        assert json_data["dimensions"] == 3
        assert json_data["model"] == "test-model"

    def test_should_deserialize_from_json(self):
        """Test deserialization."""
        data = {
            "vector": [1.0, 2.0, 3.0],
            "dimensions": 3,
            "model": "test-model",
            "normalized": False,
        }

        vector = EmbeddingVector.model_validate(data)

        assert vector.vector == [1.0, 2.0, 3.0]
        assert vector.dimensions == 3


class TestEmbeddingResult:
    """Test embedding result model."""

    def test_should_create_embedding_result(self):
        """Test basic embedding result creation."""
        embedding = EmbeddingVector.create(vector=[1.0, 2.0, 3.0], model="test-model")
        result = EmbeddingResult(
            embedding=embedding,
            text="Hello world",
            tokens=2,
            model="test-model",
        )

        assert result.text == "Hello world"
        assert result.tokens == 2
        assert result.model == "test-model"
        assert result.dimensions == 3

    def test_should_create_with_factory_method(self):
        """Test factory method creation."""
        result = EmbeddingResult.create(
            text="Hello world",
            vector=[1.0, 2.0, 3.0],
            model="test-model",
            tokens=2,
        )

        assert result.text == "Hello world"
        assert result.tokens == 2
        assert result.dimensions == 3

    def test_should_access_embedding_properties(self):
        """Test accessing embedding properties through result."""
        result = EmbeddingResult.create(
            text="Test",
            vector=[3.0, 4.0],
            model="test-model",
            tokens=1,
        )

        assert result.dimensions == 2
        assert result.is_normalized is False
        assert result.embedding.magnitude == 5.0

    def test_should_create_normalized_result(self):
        """Test creating result with normalized embedding."""
        result = EmbeddingResult.create(
            text="Test",
            vector=[3.0, 4.0],
            model="test-model",
            tokens=1,
            normalized=True,
        )

        assert result.is_normalized is True

    def test_should_serialize_to_json(self):
        """Test serialization."""
        result = EmbeddingResult.create(
            text="Hello",
            vector=[1.0, 2.0],
            model="test-model",
            tokens=1,
        )

        json_data = result.model_dump()

        assert json_data["text"] == "Hello"
        assert json_data["tokens"] == 1
        assert "embedding" in json_data

    def test_should_deserialize_from_json(self):
        """Test deserialization."""
        data = {
            "embedding": {
                "vector": [1.0, 2.0],
                "dimensions": 2,
                "model": "test-model",
                "normalized": False,
            },
            "text": "Hello",
            "tokens": 1,
            "model": "test-model",
        }

        result = EmbeddingResult.model_validate(data)

        assert result.text == "Hello"
        assert result.tokens == 1
        assert result.dimensions == 2
