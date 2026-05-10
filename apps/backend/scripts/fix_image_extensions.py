from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from PIL import Image


FORMAT_EXTENSIONS = {
    "JPEG": ".jpg",
    "PNG": ".png",
    "GIF": ".gif",
    "WEBP": ".webp",
    "BMP": ".bmp",
}


@dataclass
class FixSummary:
    scanned: int = 0
    planned: int = 0
    renamed: int = 0
    skipped: int = 0
    failed: int = 0


def detect_image_extension(path: Path) -> str | None:
    try:
        with Image.open(path) as image:
            return FORMAT_EXTENSIONS.get(image.format or "")
    except Exception:
        return None


def fix_image_extensions(root: str | Path, dry_run: bool = True) -> FixSummary:
    root_path = Path(root)
    if not root_path.exists():
        raise ValueError(f"Path does not exist: {root_path}")
    if not root_path.is_dir():
        raise ValueError(f"Path is not a directory: {root_path}")

    summary = FixSummary()

    for path in sorted(root_path.rglob("*")):
        if not path.is_file():
            continue

        detected_ext = detect_image_extension(path)
        if detected_ext is None:
            summary.skipped += 1
            continue

        summary.scanned += 1
        if path.suffix.lower() == detected_ext:
            summary.skipped += 1
            continue

        target = path.with_suffix(detected_ext)
        if target.exists():
            summary.failed += 1
            print(f"SKIP exists: {path} -> {target}")
            continue

        if dry_run:
            summary.planned += 1
            print(f"WOULD rename: {path} -> {target}")
            continue

        path.rename(target)
        summary.renamed += 1
        print(f"Renamed: {path} -> {target}")

    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detect real image formats and rename files to matching extensions."
    )
    parser.add_argument("path", help="Directory with images to scan recursively.")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually rename files. Without this flag the script runs in dry-run mode.",
    )
    args = parser.parse_args()

    summary = fix_image_extensions(args.path, dry_run=not args.apply)
    mode = "apply" if args.apply else "dry-run"
    print(
        f"Done ({mode}): scanned={summary.scanned}, planned={summary.planned}, "
        f"renamed={summary.renamed}, skipped={summary.skipped}, failed={summary.failed}"
    )

    return 1 if summary.failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
