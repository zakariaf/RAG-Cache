"""
Qdrant metadata handling utilities.

Sandi Metz Principles:
- Single Responsibility: Metadata management
- Small methods: Each operation isolated
- Clear naming: Descriptive method names
"""

import time
from typing import Any, Dict, List, Optional

from app.models.cache_entry import CacheEntry
from app.models.qdrant_schema import QdrantSchema
from app.utils.logger import get_logger

logger = get_logger(__name__)


class MetadataHandler:
    """
    Handler for point metadata operations.

    Manages metadata creation, validation, and extraction.
    """

    @staticmethod
    def create_from_cache_entry(entry: CacheEntry) -> Dict[str, Any]:
        """
        Create metadata payload from cache entry.

        Args:
            entry: Cache entry

        Returns:
            Metadata dictionary
        """
        metadata = {
            QdrantSchema.FIELD_QUERY_HASH: entry.query_hash,
            QdrantSchema.FIELD_ORIGINAL_QUERY: entry.original_query,
            QdrantSchema.FIELD_RESPONSE: entry.response,
            QdrantSchema.FIELD_PROVIDER: entry.provider,
            QdrantSchema.FIELD_MODEL: entry.model,
            QdrantSchema.FIELD_PROMPT_TOKENS: entry.prompt_tokens,
            QdrantSchema.FIELD_COMPLETION_TOKENS: entry.completion_tokens,
            QdrantSchema.FIELD_CREATED_AT: time.time(),
            QdrantSchema.FIELD_CACHED_AT: time.time(),
        }

        return metadata

    @staticmethod
    def validate_payload(payload: Dict[str, Any]) -> bool:
        """
        Validate payload has required fields.

        Args:
            payload: Payload dictionary

        Returns:
            True if valid, False otherwise
        """
        required_fields = QdrantSchema.get_required_fields()

        for field in required_fields:
            if field not in payload:
                logger.error("Missing required field", field=field)
                return False

        return True

    @staticmethod
    def extract_cache_entry(payload: Dict[str, Any]) -> Optional[CacheEntry]:
        """
        Extract cache entry from payload.

        Args:
            payload: Payload dictionary

        Returns:
            CacheEntry if valid, None otherwise
        """
        try:
            return CacheEntry(
                query_hash=payload[QdrantSchema.FIELD_QUERY_HASH],
                original_query=payload[QdrantSchema.FIELD_ORIGINAL_QUERY],
                response=payload[QdrantSchema.FIELD_RESPONSE],
                provider=payload[QdrantSchema.FIELD_PROVIDER],
                model=payload[QdrantSchema.FIELD_MODEL],
                prompt_tokens=payload.get(QdrantSchema.FIELD_PROMPT_TOKENS, 0),
                completion_tokens=payload.get(
                    QdrantSchema.FIELD_COMPLETION_TOKENS, 0
                ),
                embedding=None,
            )
        except KeyError as e:
            logger.error("Missing required field in payload", field=str(e))
            return None
        except Exception as e:
            logger.error("Cache entry extraction failed", error=str(e))
            return None

    @staticmethod
    def add_tags(payload: Dict[str, Any], tags: List[str]) -> Dict[str, Any]:
        """
        Add tags to payload.

        Args:
            payload: Existing payload
            tags: Tags to add

        Returns:
            Updated payload
        """
        existing_tags = payload.get(QdrantSchema.FIELD_TAGS, [])
        combined_tags = list(set(existing_tags + tags))
        payload[QdrantSchema.FIELD_TAGS] = combined_tags
        return payload

    @staticmethod
    def add_metadata(
        payload: Dict[str, Any], metadata: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Add custom metadata to payload.

        Args:
            payload: Existing payload
            metadata: Custom metadata

        Returns:
            Updated payload
        """
        existing_metadata = payload.get(QdrantSchema.FIELD_METADATA, {})
        existing_metadata.update(metadata)
        payload[QdrantSchema.FIELD_METADATA] = existing_metadata
        return payload

    @staticmethod
    def get_field(payload: Dict[str, Any], field: str) -> Optional[Any]:
        """
        Safely get field from payload.

        Args:
            payload: Payload dictionary
            field: Field name

        Returns:
            Field value if exists, None otherwise
        """
        return payload.get(field)

    @staticmethod
    def has_field(payload: Dict[str, Any], field: str) -> bool:
        """
        Check if payload has field.

        Args:
            payload: Payload dictionary
            field: Field name

        Returns:
            True if field exists
        """
        return field in payload

    @staticmethod
    def filter_sensitive_fields(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Remove sensitive fields from payload for logging.

        Args:
            payload: Payload dictionary

        Returns:
            Filtered payload
        """
        filtered = payload.copy()

        # Remove potentially large or sensitive fields
        sensitive_fields = [QdrantSchema.FIELD_RESPONSE]

        for field in sensitive_fields:
            if field in filtered:
                filtered[field] = "[REDACTED]"

        return filtered

    @staticmethod
    def get_metadata_summary(payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get summary of metadata for logging.

        Args:
            payload: Payload dictionary

        Returns:
            Summary dictionary
        """
        return {
            "query_hash": payload.get(QdrantSchema.FIELD_QUERY_HASH),
            "provider": payload.get(QdrantSchema.FIELD_PROVIDER),
            "model": payload.get(QdrantSchema.FIELD_MODEL),
            "prompt_tokens": payload.get(QdrantSchema.FIELD_PROMPT_TOKENS),
            "completion_tokens": payload.get(QdrantSchema.FIELD_COMPLETION_TOKENS),
            "has_tags": QdrantSchema.FIELD_TAGS in payload,
            "has_metadata": QdrantSchema.FIELD_METADATA in payload,
        }

    @staticmethod
    def merge_payloads(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge two payloads with conflict resolution.

        Args:
            base: Base payload
            updates: Update payload

        Returns:
            Merged payload
        """
        merged = base.copy()
        merged.update(updates)

        # Special handling for tags (combine)
        if QdrantSchema.FIELD_TAGS in base and QdrantSchema.FIELD_TAGS in updates:
            merged[QdrantSchema.FIELD_TAGS] = list(
                set(base[QdrantSchema.FIELD_TAGS] + updates[QdrantSchema.FIELD_TAGS])
            )

        # Special handling for metadata (merge dicts)
        if (
            QdrantSchema.FIELD_METADATA in base
            and QdrantSchema.FIELD_METADATA in updates
        ):
            merged_metadata = base[QdrantSchema.FIELD_METADATA].copy()
            merged_metadata.update(updates[QdrantSchema.FIELD_METADATA])
            merged[QdrantSchema.FIELD_METADATA] = merged_metadata

        return merged
