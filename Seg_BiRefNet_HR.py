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

# =========================
# 加载模型
# =========================
print(f"Loading model: {MODEL_ID}")
birefnet = AutoModelForImageSegmentation.from_pretrained(
    MODEL_ID,
    trust_remote_code=True
)

torch.set_float32_matmul_precision("high")

birefnet.to(DEVICE)
birefnet.eval()

if DEVICE == "cuda" and USE_FP16:
    birefnet.half()
    print("Using FP16 on CUDA")
else:
    print(f"Using device: {DEVICE}")


# =========================
# 预处理
# =========================
transform_image = transforms.Compose([
    transforms.Resize(IMAGE_SIZE),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225])
])


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

    with torch.no_grad():
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


def process_one_image(image_path: Path, mask_dir: Path, rgba_dir: Path, white_dir: Path) -> tuple[bool, str]:
    try:
        image = load_image_rgb(str(image_path))
        mask = predict_mask(birefnet, image)
        rgba = make_rgba(image, mask)
        whitebg = make_whitebg(image, mask)

        stem = image_path.stem

        mask.save(mask_dir / f"{stem}.png")
        rgba.save(rgba_dir / f"{stem}.png")
        whitebg.save(white_dir / f"{stem}.jpg", quality=95)

        return True, image_path.name
    except Exception as e:
        return False, f"{image_path.name}: {e}"


def process_one_folder(input_dir: Path, output_root: Path):
    image_files = [p for p in input_dir.iterdir() if p.is_file() and p.suffix.lower() in SUPPORTED_EXTS]
    if not image_files:
        print(f"No supported images found in {input_dir.name}.")
        return

    output_dir = output_root / input_dir.name
    mask_dir = output_dir / "masks"
    rgba_dir = output_dir / "rgba"
    white_dir = output_dir / "whitebg"

    mask_dir.mkdir(parents=True, exist_ok=True)
    rgba_dir.mkdir(parents=True, exist_ok=True)
    white_dir.mkdir(parents=True, exist_ok=True)

    print(f"\nProcessing folder: {input_dir.name}")
    print(f"Found {len(image_files)} image(s).")
    total = len(image_files)
    for idx, img_path in enumerate(image_files, start=1):
        ok, message = process_one_image(img_path, mask_dir, rgba_dir, white_dir)
        if not ok:
            print()
            print(f"[FAIL] {message}")
        print_progress(idx, total, img_path.name)

    print(f"Done: {input_dir.name}")


def main():
    input_root = Path(INPUT_ROOT)
    output_root = Path(OUTPUT_ROOT)
    if not input_root.exists():
        raise FileNotFoundError(f"Input folder not found: {INPUT_ROOT}")

    subfolders = sorted([p for p in input_root.iterdir() if p.is_dir()], key=lambda p: p.name.lower())
    if not subfolders:
        raise FileNotFoundError(f"No subfolders found in: {INPUT_ROOT}")

    output_root.mkdir(parents=True, exist_ok=True)

    total_folders = len(subfolders)
    for idx, folder_path in enumerate(subfolders, start=1):
        print(f"\n=== Folder {idx}/{total_folders} ===")
        process_one_folder(folder_path, output_root)


if __name__ == "__main__":
    main()
