import importlib.util
from pathlib import Path
from types import ModuleType


BASE_DIR = Path(__file__).resolve().parent
EXTRACT_SCRIPT = BASE_DIR / "extract_video_frames_ordered.py"
SEGMENT_SCRIPT = BASE_DIR / "Seg_BiRefNet_HR.py"


# =========================
# 配置区
# =========================
# 设为 None 时，沿用原脚本里的默认配置
VIDEO_INPUT_DIR = r"F:/Crop3DPlus/甘蓝/20260328/Video/"
FRAME_OUTPUT_DIR = r"F:/Crop3DPlus/甘蓝/20260328/RGB/"
SEG_OUTPUT_DIR = r"F:/Crop3DPlus/甘蓝/20260328/RGB-Seg/"


def load_module(module_name: str, script_path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from: {script_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def main() -> None:
    print(f"Loading extractor from: {EXTRACT_SCRIPT}")
    extract_module = load_module("extract_video_frames_ordered_module", EXTRACT_SCRIPT)

    if VIDEO_INPUT_DIR is not None:
        extract_module.INPUT_DIR = Path(VIDEO_INPUT_DIR)
    if FRAME_OUTPUT_DIR is not None:
        extract_module.OUTPUT_DIR = Path(FRAME_OUTPUT_DIR)

    frame_output = Path(extract_module.OUTPUT_DIR)

    print("\n=== Step 1/2: Extract video frames ===")
    print(f"Video input root: {Path(extract_module.INPUT_DIR)}")
    print(f"Frame output root: {frame_output}")
    extract_module.main()

    print(f"\nLoading segmenter from: {SEGMENT_SCRIPT}")
    segment_module = load_module("seg_birefnet_hr_module", SEGMENT_SCRIPT)
    segment_module.INPUT_ROOT = str(frame_output)

    if SEG_OUTPUT_DIR is not None:
        segment_module.OUTPUT_ROOT = str(Path(SEG_OUTPUT_DIR))

    print("\n=== Step 2/2: Segment extracted frames ===")
    print(f"Segmentation input root: {segment_module.INPUT_ROOT}")
    print(f"Segmentation output root: {segment_module.OUTPUT_ROOT}")
    segment_module.main()

    print("\nPipeline completed.")


if __name__ == "__main__":
    main()
