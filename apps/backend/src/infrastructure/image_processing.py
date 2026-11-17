import io

from PIL import Image, ImageOps, UnidentifiedImageError


def inspect_image(data: bytes) -> tuple[str, int, int]:
    """Validate image bytes rather than trusting a remote Content-Type header."""
    try:
        with Image.open(io.BytesIO(data)) as image:
            if image.width * image.height > 40_000_000:
                raise ValueError("Image dimensions are too large")
            mime_type = Image.MIME.get(image.format, "")
            if mime_type not in {
                "image/jpeg", "image/png", "image/gif", "image/webp", "image/bmp", "image/avif"
            }:
                raise ValueError("Unsupported image format")
            width, height = image.size
            image.verify()
        with Image.open(io.BytesIO(data)) as image:
            image.load()
        return mime_type, width, height
    except (OSError, SyntaxError, UnidentifiedImageError, Image.DecompressionBombError) as error:
        raise ValueError("Invalid or corrupted image") from error


def create_preview(data: bytes) -> bytes:
    with Image.open(io.BytesIO(data)) as image:
        image = ImageOps.exif_transpose(image)
        image.thumbnail((512, 512))
        output = io.BytesIO()
        image.convert("RGBA").save(output, format="PNG")
        return output.getvalue()
