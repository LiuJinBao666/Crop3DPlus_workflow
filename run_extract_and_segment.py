import importlib.util
from collections.abc import Callable
from pathlib import Path
from types import ModuleType


BASE_DIR = Path(__file__).resolve().parent
EXTRACT_SCRIPT = BASE_DIR / "extract_video_frames_ordered.py"
SEGMENT_SCRIPT = BASE_DIR / "Seg_BiRefNet_HR.py"


# =========================
# 配置区
# =========================
# 设为 None 时，沿用原脚本里的默认配置
VIDEO_INPUT_DIR = r"F:/Crop3DPlus/西兰花/20260416/Video/"
FRAME_OUTPUT_DIR = r"F:/Crop3DPlus/西兰花/20260416/RGB/"
SEG_OUTPUT_DIR = r"F:/Crop3DPlus/西兰花/20260416/RGB-Seg/"

LogCallback = Callable[[str], None]


def load_module(module_name: str, script_path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from: {script_path}")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_pipeline(
    *,
    video_input_dir: str | Path | None = VIDEO_INPUT_DIR,
    frame_output_dir: str | Path | None = FRAME_OUTPUT_DIR,
    seg_output_dir: str | Path | None = SEG_OUTPUT_DIR,
    logger: LogCallback = print,
) -> None:
    logger(f"Loading extractor from: {EXTRACT_SCRIPT}")
    extract_module = load_module("extract_video_frames_ordered_module", EXTRACT_SCRIPT)

    if video_input_dir is not None:
        extract_module.INPUT_DIR = Path(video_input_dir)
    if frame_output_dir is not None:
        extract_module.OUTPUT_DIR = Path(frame_output_dir)

    frame_output = Path(extract_module.OUTPUT_DIR)

    logger("\n=== Step 1/2: Extract video frames ===")
    logger(f"Video input root: {Path(extract_module.INPUT_DIR)}")
    logger(f"Frame output root: {frame_output}")
    if hasattr(extract_module, "process_root"):
        extract_module.process_root(Path(extract_module.INPUT_DIR), frame_output, logger=logger)
    else:
        extract_module.main()

    logger(f"\nLoading segmenter from: {SEGMENT_SCRIPT}")
    segment_module = load_module("seg_birefnet_hr_module", SEGMENT_SCRIPT)
    segment_module.INPUT_ROOT = str(frame_output)

    if seg_output_dir is not None:
        segment_module.OUTPUT_ROOT = str(Path(seg_output_dir))

    logger("\n=== Step 2/2: Segment extracted frames ===")
    logger(f"Segmentation input root: {segment_module.INPUT_ROOT}")
    logger(f"Segmentation output root: {segment_module.OUTPUT_ROOT}")
    if hasattr(segment_module, "process_root"):
        segment_module.process_root(segment_module.INPUT_ROOT, segment_module.OUTPUT_ROOT, logger=logger)
    else:
        segment_module.main()

    logger("\nPipeline completed.")


def main() -> None:
    run_pipeline()


if __name__ == "__main__":
    main()
