"""
Application configuration management.

Following Sandi Metz principles:
- Single Responsibility: Configuration loading and validation
- Small class: < 100 lines
- Clear naming: Descriptive property names
"""

from typing import List, Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppConfig(BaseSettings):
    """
    Application configuration with validation.

    Loads from environment variables with fallback to .env file.
    """

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, extra="ignore"
    )

    # Application settings
    app_name: str = Field(default="RAGCache", description="Application name")
    app_env: Literal["development", "staging", "production"] = Field(
        default="development", description="Environment"
    )
    log_level: str = Field(default="INFO", description="Logging level")
    debug: bool = Field(default=False, description="Debug mode")

    # API settings
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, ge=1, le=65535, description="API port")
    api_workers: int = Field(default=4, ge=1, le=32, description="Worker count")
    allowed_origins: str = Field(
        default="http://localhost:3000,http://localhost:8000",
        description="CORS allowed origins",
    )

    # Redis settings
    redis_host: str = Field(default="localhost", description="Redis host")
    redis_port: int = Field(default=6379, ge=1, le=65535, description="Redis port")
    redis_db: int = Field(default=0, ge=0, le=15, description="Redis database")
    redis_password: str = Field(default="", description="Redis password")
    redis_max_connections: int = Field(default=10, ge=1, description="Max connections")

    # Qdrant settings
    qdrant_host: str = Field(default="localhost", description="Qdrant host")
    qdrant_port: int = Field(default=6333, ge=1, le=65535, description="Qdrant port")
    qdrant_collection_name: str = Field(
        default="query_embeddings", description="Collection name"
    )
    qdrant_vector_size: int = Field(default=384, ge=1, description="Vector size")
    qdrant_grpc_port: int = Field(default=6334, ge=1, le=65535, description="gRPC port")

    # LLM Provider settings
    openai_api_key: str = Field(default="", description="OpenAI API key")
    anthropic_api_key: str = Field(default="", description="Anthropic API key")

    # Default LLM settings
    default_llm_provider: Literal["openai", "anthropic"] = Field(
        default="openai", description="Default provider"
    )
    default_model: str = Field(default="gpt-3.5-turbo", description="Default model")
    default_max_tokens: int = Field(default=1000, ge=1, description="Max tokens")
    default_temperature: float = Field(
        default=0.7, ge=0.0, le=2.0, description="Temperature"
    )

    # Embedding settings
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2", description="Embedding model"
    )
    embedding_device: Literal["cpu", "cuda"] = Field(
        default="cpu", description="Compute device"
    )
    embedding_batch_size: int = Field(default=32, ge=1, description="Batch size")

    # Cache settings
    cache_ttl_seconds: int = Field(default=3600, ge=0, description="TTL seconds")
    semantic_similarity_threshold: float = Field(
        default=0.85, ge=0.0, le=1.0, description="Similarity threshold"
    )
    enable_semantic_cache: bool = Field(
        default=True, description="Enable semantic cache"
    )
    enable_exact_cache: bool = Field(default=True, description="Enable exact cache")

    # Monitoring settings
    enable_metrics: bool = Field(default=True, description="Enable metrics")
    metrics_port: int = Field(default=9090, ge=1, le=65535, description="Metrics port")

    @field_validator("allowed_origins")
    @classmethod
    def parse_origins(cls, v: str) -> str:
        """Validate allowed origins format."""
        return v

    @property
    def allowed_origins_list(self) -> List[str]:
        """Get allowed origins as list."""
        return [origin.strip() for origin in self.allowed_origins.split(",")]

    @property
    def redis_url(self) -> str:
        """Build Redis URL."""
        if self.redis_password:
            return (
                f"redis://:{self.redis_password}@"
                f"{self.redis_host}:{self.redis_port}/{self.redis_db}"
            )
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def qdrant_url(self) -> str:
        """Build Qdrant HTTP URL."""
        return f"http://{self.qdrant_host}:{self.qdrant_port}"

    @property
    def qdrant_grpc_url(self) -> str:
        """Build Qdrant gRPC URL."""
        return f"{self.qdrant_host}:{self.qdrant_grpc_port}"

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app_env == "production"


# Global configuration instance
config = AppConfig()
