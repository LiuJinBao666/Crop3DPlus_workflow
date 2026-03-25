import shutil
from concurrent.futures import ThreadPoolExecutor
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
INPUT_DIR = Path(r"D:\photos\burst")
OUTPUT_DIR = Path(r"D:\photos\selected_100")
SELECT_COUNT = 100
WORKERS = 8
PREFIX_INDEX = True


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

    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        keyed_files = list(executor.map(lambda p: (image_sort_key(p), p), image_files))

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


def copy_selected_images(selected_images: list[Path], output_dir: Path, prefix_index: bool) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    digits = max(3, len(str(len(selected_images))))

    for idx, src in enumerate(selected_images, start=1):
        if prefix_index:
            dst_name = f"{idx:0{digits}d}_{src.name}"
        else:
            dst_name = src.name
        shutil.copy2(src, output_dir / dst_name)


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
    copy_selected_images(selected_images, OUTPUT_DIR, PREFIX_INDEX)

    print(f"Found: {len(sorted_images)} images")
    print(f"Selected: {len(selected_images)} images")
    print(f"Saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
