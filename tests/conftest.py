"""Global pytest configuration and shared fixtures for test suite."""

from __future__ import annotations

from unittest.mock import MagicMock
import pytest


@pytest.fixture
def mock_s3_client() -> MagicMock:
    """Mock boto3 S3 client for S3StorageBackend tests."""
    client = MagicMock()
    client.put_object = MagicMock(return_value={"ETag": '"test-etag"'})
    client.get_object = MagicMock(
        return_value={"Body": MagicMock(read=lambda: b"col1,col2\n1,2\n")}
    )
    client.head_object = MagicMock(return_value={})
    client.delete_object = MagicMock(return_value={})
    return client
