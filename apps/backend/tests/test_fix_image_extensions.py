import io

from PIL import Image

from scripts.fix_image_extensions import fix_image_extensions


def make_image_bytes(image_format: str) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (4, 3), color="blue").save(buffer, format=image_format)
    return buffer.getvalue()


def test_fix_image_extensions_dry_run_reports_mismatches_without_renaming(tmp_path):
    wrong_extension = tmp_path / "product.jpg"
    wrong_extension.write_bytes(make_image_bytes("PNG"))

    summary = fix_image_extensions(tmp_path, dry_run=True)

    assert summary.scanned == 1
    assert summary.renamed == 0
    assert summary.planned == 1
    assert summary.failed == 0
    assert wrong_extension.exists()
    assert not (tmp_path / "product.png").exists()


def test_fix_image_extensions_renames_files_to_detected_format(tmp_path):
    wrong_extension = tmp_path / "product.jpg"
    wrong_extension.write_bytes(make_image_bytes("PNG"))

    summary = fix_image_extensions(tmp_path, dry_run=False)

    assert summary.scanned == 1
    assert summary.renamed == 1
    assert summary.planned == 0
    assert summary.failed == 0
    assert not wrong_extension.exists()
    assert (tmp_path / "product.png").exists()


def test_fix_image_extensions_avoids_overwriting_existing_target(tmp_path):
    wrong_extension = tmp_path / "product.jpg"
    existing_target = tmp_path / "product.png"
    wrong_extension.write_bytes(make_image_bytes("PNG"))
    existing_target.write_bytes(make_image_bytes("PNG"))

    summary = fix_image_extensions(tmp_path, dry_run=False)

    assert summary.scanned == 2
    assert summary.renamed == 0
    assert summary.failed == 1
    assert wrong_extension.exists()
    assert existing_target.exists()
