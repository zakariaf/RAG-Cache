"""Test configuration module."""

from app.config import AppConfig


class TestAppConfig:
    """Test application configuration."""

    def test_should_load_default_values(self):
        """Test default configuration."""
        config = AppConfig()
        assert config.app_name == "RAGCache"
        assert config.redis_port == 6379
        assert config.api_port == 8000

    def test_should_build_redis_url(self):
        """Test Redis URL generation."""
        config = AppConfig(redis_host="localhost", redis_port=6379, redis_db=0)
        assert "redis://localhost:6379/0" in config.redis_url

    def test_should_build_redis_url_with_password(self):
        """Test Redis URL with password."""
        config = AppConfig(
            redis_host="localhost", redis_port=6379, redis_db=0, redis_password="secret"
        )
        assert "redis://:secret@localhost:6379/0" == config.redis_url

    def test_should_parse_allowed_origins(self):
        """Test allowed origins parsing."""
        config = AppConfig(
            allowed_origins="http://localhost:3000,http://localhost:8000"
        )
        origins = config.allowed_origins_list
        assert len(origins) == 2
        assert "http://localhost:3000" in origins

    def test_should_identify_development_environment(self):
        """Test environment detection."""
        config = AppConfig(app_env="development")
        assert config.is_development is True
        assert config.is_production is False
