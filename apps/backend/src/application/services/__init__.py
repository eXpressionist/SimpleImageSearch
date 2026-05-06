from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .batch_processor import BatchProcessor
    from .file_storage import FileStorageService
    from .image_downloader import ImageDownloader
    from .opencart_matcher import OpenCartImageMatcher

__all__ = ["BatchProcessor", "ImageDownloader", "FileStorageService", "OpenCartImageMatcher"]


def __getattr__(name: str):
    if name == "BatchProcessor":
        from .batch_processor import BatchProcessor

        return BatchProcessor
    if name == "ImageDownloader":
        from .image_downloader import ImageDownloader

        return ImageDownloader
    if name == "FileStorageService":
        from .file_storage import FileStorageService

        return FileStorageService
    if name == "OpenCartImageMatcher":
        from .opencart_matcher import OpenCartImageMatcher

        return OpenCartImageMatcher
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
