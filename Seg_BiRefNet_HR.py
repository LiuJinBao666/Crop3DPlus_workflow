from collections.abc import Callable
from pathlib import Path

import torch
from PIL import Image
from torchvision import transforms
from transformers import AutoModelForImageSegmentation


# =========================
# 配置区
# =========================
INPUT_ROOT = r"F:/Crop3DPlus/烟草/20260415/111/"   # 输入总文件夹，内部包含多个子文件夹
OUTPUT_ROOT = r"F:/Crop3DPlus/烟草/20260415/RGB-Seg"  # 输出总文件夹

MODEL_ID = "ZhengPeng7/BiRefNet_HR"
IMAGE_SIZE = (2048, 2048)

USE_FP16 = True   # 显卡支持的话建议 True
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}

LogCallback = Callable[[str], None]
ImageProgressCallback = Callable[[int, int, str], None]

_MODEL_CACHE = None
_MODEL_CACHE_KEY = None


def build_transform(image_size: tuple[int, int]):
    return transforms.Compose([
        transforms.Resize(image_size),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406],
                             [0.229, 0.224, 0.225])
    ])


transform_image = build_transform(IMAGE_SIZE)

# =========================
# 加载模型
# =========================
torch.set_float32_matmul_precision("high")


def resolve_device(device: str | None = None) -> str:
    if device in {None, "", "auto"}:
        return "cuda" if torch.cuda.is_available() else "cpu"
    return device


def configure_runtime(
    *,
    model_id: str | None = None,
    image_size: tuple[int, int] | None = None,
    use_fp16: bool | None = None,
    device: str | None = None,
) -> None:
    global MODEL_ID, IMAGE_SIZE, USE_FP16, DEVICE, transform_image, _MODEL_CACHE, _MODEL_CACHE_KEY

    if model_id is not None and model_id != MODEL_ID:
        MODEL_ID = model_id
        _MODEL_CACHE = None
        _MODEL_CACHE_KEY = None

    if image_size is not None and image_size != IMAGE_SIZE:
        IMAGE_SIZE = image_size
        transform_image = build_transform(IMAGE_SIZE)

    if use_fp16 is not None:
        USE_FP16 = use_fp16

    if device is not None:
        DEVICE = resolve_device(device)
        _MODEL_CACHE = None
        _MODEL_CACHE_KEY = None


def load_model(logger: LogCallback = print):
    logger(f"Loading model: {MODEL_ID}")
    model = AutoModelForImageSegmentation.from_pretrained(
        MODEL_ID,
        trust_remote_code=True
    )

    model.to(DEVICE)
    model.eval()

    if DEVICE == "cuda" and USE_FP16:
        model.half()
        logger("Using FP16 on CUDA")
    else:
        logger(f"Using device: {DEVICE}")

    return model


def get_model(logger: LogCallback = print):
    global _MODEL_CACHE, _MODEL_CACHE_KEY

    cache_key = (MODEL_ID, DEVICE, USE_FP16)
    if _MODEL_CACHE is None or _MODEL_CACHE_KEY != cache_key:
        _MODEL_CACHE = load_model(logger)
        _MODEL_CACHE_KEY = cache_key
    return _MODEL_CACHE


def print_progress(current: int, total: int, current_name: str):
    if total <= 0:
        return
    bar_width = 30
    ratio = current / total
    filled = int(bar_width * ratio)
    bar = "#" * filled + "-" * (bar_width - filled)
    print(
        f"\rProgress [{bar}] {current}/{total} ({ratio * 100:5.1f}%)  {current_name}",
        end="",
        flush=True,
    )
    if current >= total:
        print()


def load_image_rgb(image_path: str) -> Image.Image:
    return Image.open(image_path).convert("RGB")


def predict_mask(model, image: Image.Image) -> Image.Image:
    """返回与原图同尺寸的 PIL mask（L 模式）"""
    orig_size = image.size

    input_tensor = transform_image(image).unsqueeze(0).to(DEVICE)
    if DEVICE == "cuda" and USE_FP16:
        input_tensor = input_tensor.half()

    with torch.inference_mode():
        preds = model(input_tensor)[-1].sigmoid().cpu()

    pred = preds[0].squeeze(0)  # [H, W]
    pred_pil = transforms.ToPILImage()(pred)
    mask = pred_pil.resize(orig_size, Image.Resampling.BILINEAR).convert("L")
    return mask


def make_rgba(image: Image.Image, mask: Image.Image) -> Image.Image:
    """透明背景抠图"""
    rgba = image.copy().convert("RGBA")
    rgba.putalpha(mask)
    return rgba


def make_whitebg(image: Image.Image, mask: Image.Image) -> Image.Image:
    """白底合成图"""
    rgba = make_rgba(image, mask)
    white_bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))
    composed = Image.alpha_composite(white_bg, rgba)
    return composed.convert("RGB")


def process_one_image(
    image_path: Path,
    mask_dir: Path,
    rgba_dir: Path,
    white_dir: Path,
    *,
    model=None,
) -> tuple[bool, str]:
    try:
        image = load_image_rgb(str(image_path))
        resolved_model = model if model is not None else get_model()
        mask = predict_mask(resolved_model, image)
        rgba = make_rgba(image, mask)
        whitebg = make_whitebg(image, mask)

        stem = image_path.stem

        mask.save(mask_dir / f"{stem}.png")
        rgba.save(rgba_dir / f"{stem}.png")
        whitebg.save(white_dir / f"{stem}.jpg", quality=95)

        return True, image_path.name
    except Exception as e:
        return False, f"{image_path.name}: {e}"


def iter_input_folders(input_root: Path) -> list[Path]:
    subfolders = sorted([p for p in input_root.iterdir() if p.is_dir()], key=lambda p: p.name.lower())
    if not subfolders:
        raise FileNotFoundError(f"No subfolders found in: {input_root}")
    return subfolders


def count_supported_images(input_dir: Path) -> int:
    return sum(1 for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS)


def process_one_folder(
    input_dir: Path,
    output_root: Path,
    *,
    model=None,
    logger: LogCallback = print,
    progress_callback: ImageProgressCallback | None = None,
):
    image_files = sorted(
        [p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS],
        key=lambda p: p.name.lower(),
    )
    if not image_files:
        logger(f"No supported images found in {input_dir.name}.")
        return 0

    output_dir = output_root / input_dir.name
    mask_dir = output_dir / "masks"
    rgba_dir = output_dir / "rgba"
    white_dir = output_dir / "whitebg"

    mask_dir.mkdir(parents=True, exist_ok=True)
    rgba_dir.mkdir(parents=True, exist_ok=True)
    white_dir.mkdir(parents=True, exist_ok=True)

    logger(f"\nProcessing folder: {input_dir.name}")
    logger(f"Found {len(image_files)} image(s).")
    total = len(image_files)
    resolved_model = model if model is not None else get_model(logger)

    for idx, img_path in enumerate(image_files, start=1):
        ok, message = process_one_image(
            img_path,
            mask_dir,
            rgba_dir,
            white_dir,
            model=resolved_model,
        )
        if not ok:
            logger(f"[FAIL] {message}")
        if progress_callback is not None:
            progress_callback(idx, total, img_path.name)
        else:
            print_progress(idx, total, img_path.name)

    logger(f"Done: {input_dir.name}")
    return total


def process_root(
    input_root: Path | str,
    output_root: Path | str,
    *,
    logger: LogCallback = print,
    progress_callback: ImageProgressCallback | None = None,
):
    input_root_path = Path(input_root)
    output_root_path = Path(output_root)
    if not input_root_path.exists():
        raise FileNotFoundError(f"Input folder not found: {input_root_path}")

    subfolders = iter_input_folders(input_root_path)
    output_root_path.mkdir(parents=True, exist_ok=True)
    model = get_model(logger)

    total_folders = len(subfolders)
    for idx, folder_path in enumerate(subfolders, start=1):
        logger(f"\n=== Folder {idx}/{total_folders} ===")
        process_one_folder(
            folder_path,
            output_root_path,
            model=model,
            logger=logger,
            progress_callback=progress_callback,
        )

    return subfolders


def main():
    process_root(INPUT_ROOT, OUTPUT_ROOT)


if __name__ == "__main__":
    main()
