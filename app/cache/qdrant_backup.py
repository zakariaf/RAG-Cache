"""
Qdrant collection backup and restore functionality.

Sandi Metz Principles:
- Single Responsibility: Backup/restore operations
- Small methods: Each operation isolated
- Clear naming: Descriptive method names
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from qdrant_client import AsyncQdrantClient

from app.models.qdrant_point import QdrantPoint
from app.repositories.qdrant_repository import QdrantRepository
from app.utils.logger import get_logger

logger = get_logger(__name__)


class BackupFormat:
    """Backup file format constants."""

    JSON = "json"
    JSONL = "jsonl"  # JSON Lines (one JSON object per line)


class QdrantBackup:
    """
    Backup and restore Qdrant collections.

    Handles export/import of collection data.
    """

    def __init__(self, repository: QdrantRepository):
        """
        Initialize backup manager.

        Args:
            repository: Qdrant repository instance
        """
        self._repository = repository

    async def backup_to_file(
        self,
        file_path: str,
        format: str = BackupFormat.JSONL,
        batch_size: int = 100,
    ) -> bool:
        """
        Backup collection to file.

        Args:
            file_path: Path to backup file
            format: Backup format (json or jsonl)
            batch_size: Batch size for scrolling

        Returns:
            True if successful
        """
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            logger.info(
                "Starting collection backup",
                file=file_path,
                format=format,
            )

            # Get all points using pagination
            all_points: List[Dict] = []
            offset: Optional[str] = None

            while True:
                points, next_offset = await self._repository.scroll_points(
                    limit=batch_size,
                    offset=offset,
                    with_vectors=True,
                )

                if not points:
                    break

                # Convert points to dict format
                for point in points:
                    all_points.append(
                        {
                            "id": point.id,
                            "vector": point.vector,
                            "payload": point.payload,
                        }
                    )

                logger.debug(f"Backed up {len(points)} points")

                if next_offset is None:
                    break

                offset = str(next_offset)

            # Write to file
            if format == BackupFormat.JSON:
                await self._write_json(path, all_points)
            elif format == BackupFormat.JSONL:
                await self._write_jsonl(path, all_points)
            else:
                raise ValueError(f"Unsupported format: {format}")

            logger.info(
                "Collection backup completed",
                file=file_path,
                points_count=len(all_points),
            )
            return True

        except Exception as e:
            logger.error("Backup failed", error=str(e))
            return False

    async def restore_from_file(
        self,
        file_path: str,
        format: str = BackupFormat.JSONL,
        batch_size: int = 100,
        clear_existing: bool = False,
    ) -> bool:
        """
        Restore collection from file.

        Args:
            file_path: Path to backup file
            format: Backup format (json or jsonl)
            batch_size: Batch size for uploading
            clear_existing: Whether to clear existing data

        Returns:
            True if successful
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.error("Backup file not found", file=file_path)
                return False

            logger.info(
                "Starting collection restore",
                file=file_path,
                format=format,
                clear_existing=clear_existing,
            )

            # Clear existing data if requested
            if clear_existing:
                await self._repository.delete_collection()
                await self._repository.create_collection()

            # Read from file
            if format == BackupFormat.JSON:
                points_data = await self._read_json(path)
            elif format == BackupFormat.JSONL:
                points_data = await self._read_jsonl(path)
            else:
                raise ValueError(f"Unsupported format: {format}")

            # Convert to QdrantPoint objects and upload in batches
            total_restored = 0
            for i in range(0, len(points_data), batch_size):
                batch = points_data[i : i + batch_size]
                points = [
                    QdrantPoint(
                        id=p["id"],
                        vector=p["vector"],
                        payload=p["payload"],
                    )
                    for p in batch
                ]

                count = await self._repository.store_points(points)
                total_restored += count
                logger.debug(f"Restored {count} points")

            logger.info(
                "Collection restore completed",
                file=file_path,
                points_count=total_restored,
            )
            return True

        except Exception as e:
            logger.error("Restore failed", error=str(e))
            return False

    async def _write_json(self, path: Path, data: List[Dict]) -> None:
        """
        Write data as JSON array.

        Args:
            path: File path
            data: Data to write
        """
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    async def _write_jsonl(self, path: Path, data: List[Dict]) -> None:
        """
        Write data as JSON Lines.

        Args:
            path: File path
            data: Data to write
        """
        with open(path, "w") as f:
            for item in data:
                f.write(json.dumps(item) + "\n")

    async def _read_json(self, path: Path) -> List[Dict]:
        """
        Read data from JSON array.

        Args:
            path: File path

        Returns:
            List of data items
        """
        with open(path, "r") as f:
            return json.load(f)

    async def _read_jsonl(self, path: Path) -> List[Dict]:
        """
        Read data from JSON Lines.

        Args:
            path: File path

        Returns:
            List of data items
        """
        data = []
        with open(path, "r") as f:
            for line in f:
                if line.strip():
                    data.append(json.loads(line))
        return data

    async def get_backup_info(self, file_path: str) -> Optional[Dict]:
        """
        Get information about backup file.

        Args:
            file_path: Path to backup file

        Returns:
            Backup information dictionary
        """
        try:
            path = Path(file_path)
            if not path.exists():
                return None

            # Determine format
            format = (
                BackupFormat.JSONL if path.suffix == ".jsonl" else BackupFormat.JSON
            )

            # Read data
            if format == BackupFormat.JSON:
                data = await self._read_json(path)
            else:
                data = await self._read_jsonl(path)

            return {
                "file_path": str(path),
                "file_size": path.stat().st_size,
                "format": format,
                "points_count": len(data),
                "modified_time": path.stat().st_mtime,
            }

        except Exception as e:
            logger.error("Get backup info failed", error=str(e))
            return None


class SnapshotManager:
    """
    Manager for Qdrant collection snapshots.

    Uses Qdrant's native snapshot functionality.
    """

    def __init__(self, client: AsyncQdrantClient, collection_name: str):
        """
        Initialize snapshot manager.

        Args:
            client: Qdrant client
            collection_name: Collection name
        """
        self._client = client
        self._collection_name = collection_name

    async def create_snapshot(self) -> Optional[str]:
        """
        Create collection snapshot.

        Returns:
            Snapshot name if successful
        """
        try:
            result = await self._client.create_snapshot(
                collection_name=self._collection_name
            )

            logger.info(
                "Snapshot created",
                collection=self._collection_name,
                snapshot=result.name,
            )
            return result.name

        except Exception as e:
            logger.error("Snapshot creation failed", error=str(e))
            return None

    async def list_snapshots(self) -> List[Dict]:
        """
        List collection snapshots.

        Returns:
            List of snapshot information
        """
        try:
            snapshots = await self._client.list_snapshots(
                collection_name=self._collection_name
            )

            return [
                {
                    "name": snap.name,
                    "creation_time": snap.creation_time,
                    "size": snap.size,
                }
                for snap in snapshots
            ]

        except Exception as e:
            logger.error("List snapshots failed", error=str(e))
            return []

    async def delete_snapshot(self, snapshot_name: str) -> bool:
        """
        Delete collection snapshot.

        Args:
            snapshot_name: Snapshot name

        Returns:
            True if successful
        """
        try:
            await self._client.delete_snapshot(
                collection_name=self._collection_name,
                snapshot_name=snapshot_name,
            )

            logger.info(
                "Snapshot deleted",
                collection=self._collection_name,
                snapshot=snapshot_name,
            )
            return True

        except Exception as e:
            logger.error("Snapshot deletion failed", error=str(e))
            return False


async def backup_collection(
    repository: QdrantRepository,
    backup_path: str,
    format: str = BackupFormat.JSONL,
) -> bool:
    """
    Convenience function to backup collection.

    Args:
        repository: Qdrant repository
        backup_path: Path to backup file
        format: Backup format

    Returns:
        True if successful
    """
    backup = QdrantBackup(repository)
    return await backup.backup_to_file(backup_path, format=format)


async def restore_collection(
    repository: QdrantRepository,
    backup_path: str,
    format: str = BackupFormat.JSONL,
    clear_existing: bool = False,
) -> bool:
    """
    Convenience function to restore collection.

    Args:
        repository: Qdrant repository
        backup_path: Path to backup file
        format: Backup format
        clear_existing: Whether to clear existing data

    Returns:
        True if successful
    """
    backup = QdrantBackup(repository)
    return await backup.restore_from_file(
        backup_path,
        format=format,
        clear_existing=clear_existing,
    )
