import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Iterable

from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import TAGS


SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
EXIF_DATETIME_TAGS = ("DateTimeOriginal", "DateTimeDigitized", "DateTime")

# =========================
# 配置区
# =========================
INPUT_DIR = Path(r"F:/Crop3DPlus/烟草/20260325/RGB/YY-23")
OUTPUT_DIR = Path(r"F:/Crop3DPlus/烟草/20260325/RGB/YY-23_100")
SELECT_COUNT = 100
WORKERS = 8


def print_progress(current: int, total: int, prefix: str) -> None:
    if total <= 0:
        return
    bar_width = 30
    ratio = current / total
    filled = int(bar_width * ratio)
    bar = "#" * filled + "-" * (bar_width - filled)
    print(f"\r{prefix} [{bar}] {current}/{total} ({ratio * 100:5.1f}%)", end="", flush=True)
    if current >= total:
        print()


def iter_image_files(input_dir: Path) -> Iterable[Path]:
    for path in input_dir.iterdir():
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTS:
            yield path


def exif_datetime_from_path(path: Path) -> datetime | None:
    try:
        with Image.open(path) as img:
            exif = img.getexif()
            if not exif:
                return None

            for tag_id, value in exif.items():
                tag_name = TAGS.get(tag_id, tag_id)
                if tag_name not in EXIF_DATETIME_TAGS or not value:
                    continue
                try:
                    return datetime.strptime(str(value), "%Y:%m:%d %H:%M:%S")
                except ValueError:
                    continue
    except (UnidentifiedImageError, OSError):
        return None
    return None


def image_sort_key(path: Path) -> tuple[datetime, str]:
    captured_at = exif_datetime_from_path(path)
    if captured_at is None:
        captured_at = datetime.fromtimestamp(path.stat().st_mtime)
    return captured_at, path.name.lower()


def collect_sorted_images(input_dir: Path, workers: int) -> list[Path]:
    image_files = list(iter_image_files(input_dir))
    if not image_files:
        return []

    total = len(image_files)
    print(f"Reading metadata for {total} image(s)...")
    keyed_files = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        future_map = {executor.submit(image_sort_key, path): path for path in image_files}
        for idx, future in enumerate(as_completed(future_map), start=1):
            path = future_map[future]
            keyed_files.append((future.result(), path))
            print_progress(idx, total, "Scanning")

    keyed_files.sort(key=lambda item: item[0])
    return [path for _, path in keyed_files]


def select_evenly(sorted_images: list[Path], count: int) -> list[Path]:
    total = len(sorted_images)
    if count >= total:
        return sorted_images[:]
    if count <= 0:
        return []

    step = (total - 1) / (count - 1) if count > 1 else 0
    indices = []
    for i in range(count):
        index = int(round(i * step))
        if indices and index <= indices[-1]:
            index = min(indices[-1] + 1, total - 1)
        indices.append(index)
    return [sorted_images[i] for i in indices]


def copy_selected_images(selected_images: list[Path], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    total = len(selected_images)
    print(f"Copying {total} selected image(s)...")

    for idx, src in enumerate(selected_images, start=1):
        dst_name = f"{idx}{src.suffix.lower()}"
        shutil.copy2(src, output_dir / dst_name)
        print_progress(idx, total, "Copying ")


def main() -> None:
    if not INPUT_DIR.exists() or not INPUT_DIR.is_dir():
        raise FileNotFoundError(f"Input folder not found: {INPUT_DIR}")
    if SELECT_COUNT <= 0:
        raise ValueError("SELECT_COUNT must be greater than 0")

    sorted_images = collect_sorted_images(INPUT_DIR, WORKERS)
    if not sorted_images:
        print("No supported images found.")
        return

    selected_images = select_evenly(sorted_images, SELECT_COUNT)
    copy_selected_images(selected_images, OUTPUT_DIR)

    print(f"Found: {len(sorted_images)} images")
    print(f"Selected: {len(selected_images)} images")
    print(f"Saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
