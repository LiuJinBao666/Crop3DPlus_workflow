from __future__ import annotations

import importlib
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


LogCallback = Callable[[str], None]
ProgressCallback = Callable[[int, str], None]


def _get_extractor():
    return importlib.import_module("extract_video_frames_ordered")


def _get_segmenter():
    return importlib.import_module("Seg_BiRefNet_HR")


def _is_cuda_available() -> bool:
    try:
        torch = importlib.import_module("torch")
    except ModuleNotFoundError:
        return False
    return bool(torch.cuda.is_available())


@dataclass(slots=True)
class ExtractConfig:
    input_dir: Path
    output_dir: Path
    frames_per_main_video: int = 33
    frames_for_top_video: int = 3
    top_video_max_duration: float = 10.0
    ffmpeg_cmd: str = "ffmpeg"
    ffprobe_cmd: str = "ffprobe"


@dataclass(slots=True)
class SegmentConfig:
    input_root: Path
    output_root: Path
    model_id: str = "ZhengPeng7/BiRefNet_HR"
    image_width: int = 2048
    image_height: int = 2048
    use_fp16: bool = True
    device: str = "auto"


@dataclass(slots=True)
class PipelineConfig:
    video_input_dir: Path
    frame_output_dir: Path
    seg_output_dir: Path
    frames_per_main_video: int = 33
    frames_for_top_video: int = 3
    top_video_max_duration: float = 10.0
    ffmpeg_cmd: str = "ffmpeg"
    ffprobe_cmd: str = "ffprobe"
    model_id: str = "ZhengPeng7/BiRefNet_HR"
    image_width: int = 2048
    image_height: int = 2048
    use_fp16: bool = True
    device: str = "auto"


class TaskRunner:
    def __init__(self, log_callback: LogCallback, progress_callback: ProgressCallback):
        self._log_callback = log_callback
        self._progress_callback = progress_callback

    def log(self, message: str) -> None:
        self._log_callback(message)

    def set_progress(self, percent: int, message: str) -> None:
        bounded = max(0, min(100, percent))
        self._progress_callback(bounded, message)

    def _set_scaled_progress(self, base: int, span: int, percent: int, message: str) -> None:
        absolute = base + round(span * max(0, min(100, percent)) / 100)
        self.set_progress(absolute, message)

    @staticmethod
    def _ensure_existing_directory(path: Path, label: str) -> Path:
        resolved = path.expanduser().resolve()
        if not resolved.exists() or not resolved.is_dir():
            raise FileNotFoundError(f"{label} does not exist or is not a folder: {resolved}")
        return resolved

    @staticmethod
    def _ensure_output_root(path: Path) -> Path:
        resolved = path.expanduser().resolve()
        resolved.mkdir(parents=True, exist_ok=True)
        return resolved

    @staticmethod
    def _validate_binary(command: str, label: str) -> str:
        value = command.strip()
        if not value:
            raise ValueError(f"{label} cannot be empty.")

        candidate = Path(value)
        if candidate.exists():
            return str(candidate)

        if shutil.which(value) is None:
            raise FileNotFoundError(f"{label} was not found: {value}")
        return value

    @staticmethod
    def _validate_positive_int(value: int, label: str) -> int:
        if value <= 0:
            raise ValueError(f"{label} must be greater than 0.")
        return value

    @staticmethod
    def _validate_positive_float(value: float, label: str) -> float:
        if value <= 0:
            raise ValueError(f"{label} must be greater than 0.")
        return value

    def run_extract(self, config: ExtractConfig, *, progress_base: int = 0, progress_span: int = 100) -> None:
        extractor = _get_extractor()
        input_dir = self._ensure_existing_directory(config.input_dir, "Video input folder")
        output_dir = self._ensure_output_root(config.output_dir)

        extractor.FRAMES_PER_MAIN_VIDEO = self._validate_positive_int(
            config.frames_per_main_video,
            "Frames per main video",
        )
        extractor.FRAMES_FOR_TOP_VIDEO = self._validate_positive_int(
            config.frames_for_top_video,
            "Frames for top video",
        )
        extractor.TOP_VIDEO_MAX_DURATION = self._validate_positive_float(
            config.top_video_max_duration,
            "Top video max duration",
        )
        extractor.FFMPEG_CMD = self._validate_binary(config.ffmpeg_cmd, "ffmpeg command")
        extractor.FFPROBE_CMD = self._validate_binary(config.ffprobe_cmd, "ffprobe command")

        folders = extractor.iter_input_folders(input_dir)
        total_folders = len(folders)

        self.log(f"Video input root: {input_dir}")
        self.log(f"Frame output root: {output_dir}")
        self.log(f"Found {total_folders} folder(s) for frame extraction.")

        if total_folders == 0:
            self._set_scaled_progress(progress_base, progress_span, 100, "No folders to process.")
            return

        for index, folder in enumerate(folders, start=1):
            start_percent = int((index - 1) * 100 / total_folders)
            self._set_scaled_progress(
                progress_base,
                progress_span,
                start_percent,
                f"Extracting folder {index}/{total_folders}: {folder.name}",
            )
            extractor.process_one_folder(folder, output_dir / folder.name, logger=self.log)
            done_percent = int(index * 100 / total_folders)
            self._set_scaled_progress(
                progress_base,
                progress_span,
                done_percent,
                f"Finished extracting {folder.name}",
            )

    def run_segment(self, config: SegmentConfig, *, progress_base: int = 0, progress_span: int = 100) -> None:
        segmenter = _get_segmenter()
        input_root = self._ensure_existing_directory(config.input_root, "Segmentation input folder")
        output_root = self._ensure_output_root(config.output_root)

        width = self._validate_positive_int(config.image_width, "Image width")
        height = self._validate_positive_int(config.image_height, "Image height")
        device = config.device.strip().lower() or "auto"

        if device == "cuda" and not _is_cuda_available():
            raise RuntimeError("CUDA was selected, but no CUDA device is available.")
        if device not in {"auto", "cuda", "cpu"}:
            raise ValueError(f"Unsupported device option: {config.device}")

        segmenter.configure_runtime(
            model_id=config.model_id.strip() or segmenter.MODEL_ID,
            image_size=(width, height),
            use_fp16=config.use_fp16,
            device=device,
        )

        folders = segmenter.iter_input_folders(input_root)
        total_folders = len(folders)
        total_images = sum(segmenter.count_supported_images(folder) for folder in folders)

        self.log(f"Segmentation input root: {input_root}")
        self.log(f"Segmentation output root: {output_root}")
        self.log(f"Found {total_folders} folder(s), total images: {total_images}.")

        if total_images == 0:
            for index, folder in enumerate(folders, start=1):
                segmenter.process_one_folder(folder, output_root, logger=self.log)
                done_percent = int(index * 100 / total_folders)
                self._set_scaled_progress(
                    progress_base,
                    progress_span,
                    done_percent,
                    f"Finished scanning {folder.name}",
                )
            return

        processed_images = 0
        model = segmenter.get_model(self.log)

        for folder_index, folder in enumerate(folders, start=1):
            folder_total = segmenter.count_supported_images(folder)

            def on_folder_progress(current: int, total: int, current_name: str) -> None:
                absolute_current = processed_images + current
                percent = int(absolute_current * 100 / total_images)
                self._set_scaled_progress(
                    progress_base,
                    progress_span,
                    percent,
                    f"{folder.name} | {current}/{total} | {current_name}",
                )

            processed_count = segmenter.process_one_folder(
                folder,
                output_root,
                model=model,
                logger=self.log,
                progress_callback=on_folder_progress if folder_total > 0 else None,
            )
            processed_images += processed_count
            done_percent = int(processed_images * 100 / total_images)
            self._set_scaled_progress(
                progress_base,
                progress_span,
                done_percent,
                f"Finished segmentation for {folder_index}/{total_folders}: {folder.name}",
            )

    def run_pipeline(self, config: PipelineConfig) -> None:
        self.log("=== Step 1/2: Extract video frames ===")
        self.run_extract(
            ExtractConfig(
                input_dir=config.video_input_dir,
                output_dir=config.frame_output_dir,
                frames_per_main_video=config.frames_per_main_video,
                frames_for_top_video=config.frames_for_top_video,
                top_video_max_duration=config.top_video_max_duration,
                ffmpeg_cmd=config.ffmpeg_cmd,
                ffprobe_cmd=config.ffprobe_cmd,
            ),
            progress_base=0,
            progress_span=35,
        )

        self.log("\n=== Step 2/2: Segment extracted frames ===")
        self.run_segment(
            SegmentConfig(
                input_root=config.frame_output_dir,
                output_root=config.seg_output_dir,
                model_id=config.model_id,
                image_width=config.image_width,
                image_height=config.image_height,
                use_fp16=config.use_fp16,
                device=config.device,
            ),
            progress_base=35,
            progress_span=65,
        )
