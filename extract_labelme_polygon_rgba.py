import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageOps


# =========================
# 配置区
# =========================
IMAGES_DIR = Path(r"F:/烟草训练/images")
JSON_DIR = Path(r"F:/烟草训练/labels")
OUTPUT_DIR = Path(r"F:/烟草训练/whitebg")

SUPPORTED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
ONLY_POLYGON = True


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


def find_image_for_json(json_path: Path) -> Path:
    stem = json_path.stem

    with json_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    image_path_value = data.get("imagePath")
    if image_path_value:
        candidate = IMAGES_DIR / Path(image_path_value).name
        if candidate.exists():
            return candidate

    for ext in SUPPORTED_IMAGE_EXTS:
        candidate = IMAGES_DIR / f"{stem}{ext}"
        if candidate.exists():
            return candidate

    raise FileNotFoundError(f"No matching image found for json: {json_path.name}")


def build_mask(image_size: tuple[int, int], shapes: list[dict]) -> Image.Image:
    mask = Image.new("L", image_size, 0)
    draw = ImageDraw.Draw(mask)

    for shape in shapes:
        shape_type = shape.get("shape_type", "polygon")
        if ONLY_POLYGON and shape_type != "polygon":
            continue

        points = shape.get("points", [])
        if len(points) < 3:
            continue

        polygon_points = [(float(x), float(y)) for x, y in points]
        draw.polygon(polygon_points, fill=255)

    return mask


def process_one_json(json_path: Path) -> tuple[bool, str]:
    try:
        image_path = find_image_for_json(json_path)

        with json_path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        shapes = data.get("shapes", [])
        if not shapes:
            return False, f"{json_path.name}: no shapes found"

        image = Image.open(image_path)
        image = ImageOps.exif_transpose(image).convert("RGBA")
        mask = build_mask(image.size, shapes)

        if mask.getbbox() is None:
            return False, f"{json_path.name}: no valid polygon found"

        image.putalpha(mask)
        white_bg = Image.new("RGBA", image.size, (255, 255, 255, 255))
        image = Image.alpha_composite(white_bg, image).convert("RGB")
        output_path = OUTPUT_DIR / f"{image_path.stem}.png"
        image.save(output_path)
        return True, image_path.name
    except Exception as e:
        return False, f"{json_path.name}: {e}"


def main() -> None:
    if not IMAGES_DIR.exists() or not IMAGES_DIR.is_dir():
        raise FileNotFoundError(f"Images folder not found: {IMAGES_DIR}")
    if not JSON_DIR.exists() or not JSON_DIR.is_dir():
        raise FileNotFoundError(f"JSON folder not found: {JSON_DIR}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    json_files = sorted(JSON_DIR.glob("*.json"))
    if not json_files:
        print("No json files found.")
        return

    total = len(json_files)
    failed = 0

    print(f"Found {total} json file(s).")
    for idx, json_path in enumerate(json_files, start=1):
        ok, message = process_one_json(json_path)
        if not ok:
            failed += 1
            print()
            print(f"[FAIL] {message}")
        print_progress(idx, total, "Processing")

    print(f"Done. Success: {total - failed}, Failed: {failed}")
    print(f"Saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
