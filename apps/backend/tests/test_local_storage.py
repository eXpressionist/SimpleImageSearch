import io

import pytest
from PIL import Image

from src.infrastructure.providers.local_storage import LocalFileStorage


def make_image_bytes(image_format: str) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (3, 2), color="red").save(buffer, format=image_format)
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_save_uses_detected_image_format_over_filename_and_content_type(tmp_path):
    storage = LocalFileStorage(base_path=str(tmp_path))
    data = make_image_bytes("PNG")

    result = await storage.save(
        data=data,
        batch_id="batch-1",
        item_id="item-1",
        filename="search_result.jpg",
        content_type="image/jpeg",
    )

    assert result.file_name == "search_result.png"
    assert result.mime_type == "image/png"
    assert result.width == 3
    assert result.height == 2
    assert (tmp_path / "batch-1" / "item-1" / "search_result.png").exists()
    assert not (tmp_path / "batch-1" / "item-1" / "search_result.jpg").exists()


@pytest.mark.asyncio
async def test_save_to_directory_uses_flat_target_directory_and_preserves_filename_extension(tmp_path):
    storage = LocalFileStorage(base_path=str(tmp_path / "storage"))
    data = make_image_bytes("PNG")
    target_dir = tmp_path / "exports"

    result = await storage.save_to_directory(
        data=data,
        target_dir=str(target_dir),
        filename="SKU-1.jpg",
        content_type="image/png",
    )

    assert result.file_name == "SKU-1.jpg"
    assert result.mime_type == "image/png"
    assert (target_dir / "SKU-1.jpg").exists()
    assert not (target_dir / "batch-1").exists()
