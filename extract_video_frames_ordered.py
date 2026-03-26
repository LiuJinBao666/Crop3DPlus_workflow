import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


# =========================
# 配置区
# =========================
INPUT_DIR = Path(r"F:/Crop3DPlus/烟草/20260325/RGB/CB-30")
OUTPUT_DIR = Path(r"F:/Crop3DPlus/烟草/20260325/RGB/CB-30_100")
FRAMES_PER_VIDEO = 33
FFMPEG_CMD = "ffmpeg"
FFPROBE_CMD = "ffprobe"

VIDEO_EXTS = {".mp4"}
IMAGE_EXTS = {".jpg", ".jpeg"}
DATETIME_FORMATS = (
    "%Y-%m-%dT%H:%M:%S.%fZ",
    "%Y-%m-%dT%H:%M:%SZ",
    "%Y-%m-%d %H:%M:%S",
    "%Y:%m:%d %H:%M:%S",
)


def run_command(command: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(command, capture_output=True, text=True, check=True)


def parse_datetime(value: str) -> datetime | None:
    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def get_video_metadata(video_path: Path) -> tuple[datetime, float]:
    command = [
        FFPROBE_CMD,
        "-v",
        "quiet",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        str(video_path),
    ]
    result = run_command(command)
    data = json.loads(result.stdout)

    format_info = data.get("format", {})
    streams = data.get("streams", [])
    tags_to_check = []

    if isinstance(format_info.get("tags"), dict):
        tags_to_check.append(format_info["tags"])

    for stream in streams:
        if isinstance(stream.get("tags"), dict):
            tags_to_check.append(stream["tags"])

    captured_at = None
    for tags in tags_to_check:
        for key in ("creation_time", "com.apple.quicktime.creationdate", "date"):
            value = tags.get(key)
            if not value:
                continue
            captured_at = parse_datetime(str(value))
            if captured_at is not None:
                break
        if captured_at is not None:
            break

    if captured_at is None:
        captured_at = datetime.fromtimestamp(video_path.stat().st_mtime)

    duration_str = format_info.get("duration")
    if duration_str is None:
        raise ValueError(f"Cannot read duration from: {video_path}")

    duration = float(duration_str)
    if duration <= 0:
        raise ValueError(f"Invalid duration for: {video_path}")

    return captured_at, duration


def collect_inputs(input_dir: Path) -> tuple[list[Path], Path]:
    files = [p for p in input_dir.iterdir() if p.is_file()]
    video_files = [p for p in files if p.suffix.lower() in VIDEO_EXTS]
    image_files = [p for p in files if p.suffix.lower() in IMAGE_EXTS]

    if len(video_files) != 3:
        raise ValueError(f"Expected exactly 3 mp4 files, found {len(video_files)}")
    if len(image_files) != 1:
        raise ValueError(f"Expected exactly 1 jpg file, found {len(image_files)}")

    return video_files, image_files[0]


def extract_frames(video_path: Path, output_dir: Path, start_index: int, count: int, duration: float) -> None:
    fps = count / duration
    output_pattern = str(output_dir / "%d.jpg")
    command = [
        FFMPEG_CMD,
        "-y",
        "-i",
        str(video_path),
        "-vf",
        f"fps={fps:.12f}",
        "-q:v",
        "2",
        "-frames:v",
        str(count),
        "-start_number",
        str(start_index),
        output_pattern,
    ]
    subprocess.run(command, check=True)


def main() -> None:
    if not INPUT_DIR.exists() or not INPUT_DIR.is_dir():
        raise FileNotFoundError(f"Input folder not found: {INPUT_DIR}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    video_files, source_image = collect_inputs(INPUT_DIR)

    video_infos = []
    for video_path in video_files:
        captured_at, duration = get_video_metadata(video_path)
        video_infos.append((captured_at, video_path.name.lower(), video_path, duration))

    video_infos.sort(key=lambda item: (item[0], item[1]))

    current_index = 1
    for order, (_, _, video_path, duration) in enumerate(video_infos, start=1):
        print(f"[{order}/3] Extracting {FRAMES_PER_VIDEO} frame(s) from {video_path.name} ...")
        extract_frames(video_path, OUTPUT_DIR, current_index, FRAMES_PER_VIDEO, duration)
        current_index += FRAMES_PER_VIDEO

    final_image_path = OUTPUT_DIR / "100.jpg"
    shutil.copy2(source_image, final_image_path)

    print("Done.")
    print(f"Frames saved to: {OUTPUT_DIR}")
    print(f"Final still image saved as: {final_image_path.name}")


if __name__ == "__main__":
    main()
