"""Unit tests for StorageService and StorageBackend implementations."""

from __future__ import annotations

from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from app.core.storage import LocalStorageBackend, S3StorageBackend, StorageService


def test_storage_service_save_and_read_local(tmp_path) -> None:
    backend = LocalStorageBackend(base_dir=tmp_path / "uploads")
    service = StorageService(backend=backend)

    ws_id = uuid4()
    ds_id = uuid4()
    content = b"col1,col2\n1,2\n3,4\n"

    key = service.save_dataset_file(ws_id, ds_id, "dataset.csv", content)
    assert key == f"workspaces/{ws_id}/datasets/{ds_id}.csv"

    read_bytes = service.read_dataset_file(key)
    assert read_bytes == content


def test_storage_service_save_and_read_s3(mock_s3_client: MagicMock) -> None:
    backend = S3StorageBackend(bucket_name="test-bucket", s3_client=mock_s3_client)
    service = StorageService(backend=backend)

    ws_id = uuid4()
    ds_id = uuid4()
    content = b"a,b,c\n10,20,30\n"

    saved_bytes: list[bytes] = []

    def fake_put_object(Bucket, Key, Body, **kwargs):
        saved_bytes.append(Body)

    mock_s3_client.put_object.side_effect = fake_put_object

    key = service.save_dataset_file(ws_id, ds_id, "sample.csv", content)
    assert key == f"workspaces/{ws_id}/datasets/{ds_id}.csv"

    mock_body = MagicMock()
    mock_body.read.return_value = content
    mock_s3_client.get_object.return_value = {"Body": mock_body}

    read_bytes = service.read_dataset_file(key)
    assert read_bytes == content


def test_storage_service_path_traversal_prevention(tmp_path) -> None:
    backend = LocalStorageBackend(base_dir=tmp_path / "uploads")
    service = StorageService(backend=backend)
    ws_id = uuid4()
    ds_id = uuid4()

    with pytest.raises(ValueError, match="Invalid filename"):
        service.save_dataset_file(ws_id, ds_id, "../malicious.csv", b"data")
