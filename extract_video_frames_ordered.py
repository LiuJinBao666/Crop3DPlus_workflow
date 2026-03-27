import subprocess
from datetime import datetime
from pathlib import Path


# =========================
# 配置区
# =========================
INPUT_DIR = Path(r"F:/Crop3DPlus/西兰花/20260327/Video/")
OUTPUT_DIR = Path(r"F:/Crop3DPlus/西兰花/20260327/RGB/")
FRAMES_PER_MAIN_VIDEO = 33
FRAMES_FOR_TOP_VIDEO = 3
TOP_VIDEO_NAME = "top.mp4"
FFMPEG_CMD = "ffmpeg"
FFPROBE_CMD = "ffprobe"

VIDEO_EXTS = {".mp4"}
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
        "error",
        "-show_entries",
        "format=duration:format_tags=creation_time:stream_tags=creation_time,com.apple.quicktime.creationdate,date",
        "-of",
        "default=noprint_wrappers=1",
        str(video_path),
    ]
    result = run_command(command)

    duration = None
    captured_at = None
    for raw_line in result.stdout.splitlines():
        line = raw_line.strip()
        if not line or "=" not in line:
            continue

        key, value = line.split("=", 1)
        if key == "duration":
            try:
                duration = float(value)
            except ValueError:
                pass
            continue

        if key in {"TAG:creation_time", "TAG:com.apple.quicktime.creationdate", "TAG:date"} and captured_at is None:
            captured_at = parse_datetime(value)

    if captured_at is None:
        captured_at = datetime.fromtimestamp(video_path.stat().st_mtime)

    if duration is None:
        raise ValueError(f"Cannot read duration from: {video_path}")
    if duration <= 0:
        raise ValueError(f"Invalid duration for: {video_path}")

    return captured_at, duration


def collect_inputs(input_dir: Path) -> tuple[list[Path], Path | None]:
    files = [p for p in input_dir.iterdir() if p.is_file()]
    video_files = [p for p in files if p.suffix.lower() in VIDEO_EXTS]
    top_video = None
    normal_videos = []

    for video_path in video_files:
        if video_path.name.lower() == TOP_VIDEO_NAME.lower():
            top_video = video_path
        else:
            normal_videos.append(video_path)

    if top_video is not None:
        if len(normal_videos) != 3:
            raise ValueError(f"Expected 3 normal mp4 files plus {TOP_VIDEO_NAME}, found {len(normal_videos)} normal video(s)")
    else:
        if len(normal_videos) != 3:
            raise ValueError(f"Expected exactly 3 mp4 files when {TOP_VIDEO_NAME} is absent, found {len(normal_videos)}")

    return normal_videos, top_video


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


def build_video_infos(folder_path: Path) -> list[tuple[datetime, str, Path, float, int]]:
    normal_videos, top_video = collect_inputs(folder_path)
    video_infos = []
    for video_path in normal_videos:
        captured_at, duration = get_video_metadata(video_path)
        video_infos.append((captured_at, video_path.name.lower(), video_path, duration, FRAMES_PER_MAIN_VIDEO))

    video_infos.sort(key=lambda item: (item[0], item[1]))

    if top_video is not None:
        captured_at, duration = get_video_metadata(top_video)
        video_infos.append((captured_at, top_video.name.lower(), top_video, duration, FRAMES_FOR_TOP_VIDEO))

    return video_infos


def process_one_folder(folder_path: Path, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    video_infos = build_video_infos(folder_path)

    current_index = 1
    total_videos = len(video_infos)
    print(f"\nProcessing folder: {folder_path.name}")
    for order, (_, _, video_path, duration, frame_count) in enumerate(video_infos, start=1):
        print(f"[{order}/{total_videos}] Extracting {frame_count} frame(s) from {video_path.name} ...")
        extract_frames(video_path, output_dir, current_index, frame_count, duration)
        current_index += frame_count

    print(f"Done: {folder_path.name}")
    print(f"Frames saved to: {output_dir}")
    print(f"Total images: {current_index - 1}")


def main() -> None:
    if not INPUT_DIR.exists() or not INPUT_DIR.is_dir():
        raise FileNotFoundError(f"Input folder not found: {INPUT_DIR}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    subfolders = sorted([p for p in INPUT_DIR.iterdir() if p.is_dir()], key=lambda p: p.name.lower())
    if not subfolders:
        raise FileNotFoundError(f"No subfolders found in: {INPUT_DIR}")

    total_folders = len(subfolders)
    for idx, folder_path in enumerate(subfolders, start=1):
        print(f"\n=== Folder {idx}/{total_folders} ===")
        process_one_folder(folder_path, OUTPUT_DIR / folder_path.name)


if __name__ == "__main__":
    main()
