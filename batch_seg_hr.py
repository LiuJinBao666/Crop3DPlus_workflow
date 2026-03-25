import os
from pathlib import Path

import torch
from PIL import Image
from torchvision import transforms
from transformers import AutoModelForImageSegmentation


# =========================
# 配置区
# =========================
INPUT_DIR = r"./images/烟草"              # 输入图片文件夹
OUTPUT_MASK_DIR = r"./outputs/烟草/masks" # 输出 mask
OUTPUT_RGBA_DIR = r"./outputs/烟草/rgba"  # 输出透明背景图
OUTPUT_WHITE_DIR = r"./outputs/烟草/whitebg"  # 输出白底图

MODEL_ID = "ZhengPeng7/BiRefNet_HR"
IMAGE_SIZE = (2048, 2048)

USE_FP16 = True   # 显卡支持的话建议 True
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


# =========================
# 创建输出目录
# =========================
Path(OUTPUT_MASK_DIR).mkdir(parents=True, exist_ok=True)
Path(OUTPUT_RGBA_DIR).mkdir(parents=True, exist_ok=True)
Path(OUTPUT_WHITE_DIR).mkdir(parents=True, exist_ok=True)


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


def process_one_image(image_path: Path):
    try:
        image = load_image_rgb(str(image_path))
        mask = predict_mask(birefnet, image)
        rgba = make_rgba(image, mask)
        whitebg = make_whitebg(image, mask)

        stem = image_path.stem

        mask.save(Path(OUTPUT_MASK_DIR) / f"{stem}_mask.png")
        rgba.save(Path(OUTPUT_RGBA_DIR) / f"{stem}_rgba.png")
        whitebg.save(Path(OUTPUT_WHITE_DIR) / f"{stem}_whitebg.jpg", quality=95)

        print(f"[OK] {image_path.name}")
    except Exception as e:
        print(f"[FAIL] {image_path.name}: {e}")


def main():
    input_dir = Path(INPUT_DIR)
    if not input_dir.exists():
        raise FileNotFoundError(f"Input folder not found: {INPUT_DIR}")

    image_files = [p for p in input_dir.iterdir() if p.suffix.lower() in SUPPORTED_EXTS]
    if not image_files:
        print("No supported images found.")
        return

    print(f"Found {len(image_files)} image(s).")
    for img_path in image_files:
        process_one_image(img_path)

    print("Done.")


if __name__ == "__main__":
    main()