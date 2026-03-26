import os
from pathlib import Path
import subprocess
from typing import Union, Optional

def get_files_with_extension_advanced(directory, extension, recursive=False):
    """
    Get files with specific extension - supports recursion and uses pathlib.
    """
    if not extension.startswith('.'):
        extension = '.' + extension
    
    directory = Path(directory)
    
    if recursive:
        pattern = f"**/*{extension}"
    else:
        pattern = f"*{extension}"
    
    files = [f.name for f in directory.glob(pattern) if f.is_file()]
    
    return sorted(files)
	

def convert_to_mp4(
    input_file: Union[str, Path],
    output_mp4: Optional[Union[str, Path]] = None,
    overwrite: bool = True,
    quiet: bool = False,
    copy_streams: bool = True,
    convert_subtitles: bool = True,
    faststart: bool = True,
    fix_ts_issues: bool = True,           # only used when input looks like .ts
    reencode_video_preset: str = "medium",
    reencode_crf: int = 23,
    reencode_audio_bitrate: str = "192k",
) -> bool:
    """
    Convert video file (.mkv, .ts, .m2ts, .avi, etc.) → .mp4 using ffmpeg.
    Prefers fast stream copy (remux) when possible.

    Parameters
    ----------
    input_file : str | Path
        Input video file (mkv, ts, etc.)

    output_mp4 : str | Path, optional
        Output .mp4 path. If None → same name + .mp4

    overwrite : bool
        Overwrite output if it exists

    quiet : bool
        Hide most ffmpeg output

    copy_streams : bool
        True  → remux / copy streams (fastest, no quality loss) – recommended
        False → re-encode to H.264 + AAC (slower, higher compatibility)

    convert_subtitles : bool
        When copy_streams=True: convert subs → mov_text (MP4 compatible)
        When copy_streams=False: always uses mov_text

    faststart : bool
        Add -movflags +faststart (better for streaming / progressive playback)

    fix_ts_issues : bool
        For .ts / .m2ts files: add common flags to repair timestamps & AAC audio

    reencode_video_preset : str
        When re-encoding: slow/medium/fast/veryfast/ultrafast

    reencode_crf : int
        When re-encoding video: 18–28 range (lower = better quality, bigger file)

    reencode_audio_bitrate : str
        When re-encoding audio: e.g. "128k", "192k", "256k"

    Returns
    -------
    bool : True if conversion finished successfully
    """
    input_path = Path(input_file).resolve()
    if not input_path.is_file():
        print(f"Error: Input file not found → {input_path}")
        return False

    if output_mp4 is None:
        output_path = input_path.with_suffix(".mp4")
    else:
        output_path = Path(output_mp4).resolve()

    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists() and not overwrite:
        print(f"Skipping (already exists): {output_path.name}")
        return True

    print(f"Converting: {input_path.name}")
    print(f"       →    {output_path.name}")

    is_ts_like = input_path.suffix.lower() in {".ts", ".m2ts", ".mts", ".tp"}

    cmd = ["ffmpeg", "-i", str(input_path)]

    # ─── Common .ts / transport stream fixes ───────────────────────────────
    if is_ts_like and fix_ts_issues:
        cmd.extend([
            "-fflags", "+genpts+discardcorrupt+igndts",
            "-bsf:a", "aac_adtstoasc",          # fixes many AAC audio issues in .ts
        ])

    # ─── Mapping & codec choices ────────────────────────────────────────────
    if copy_streams:
        cmd.extend(["-map", "0"])
        cmd.extend(["-c:v", "copy", "-c:a", "copy"])

        if convert_subtitles:
            cmd.extend(["-c:s", "mov_text"])
        else:
            cmd.extend(["-sn"])                     # strip subtitles

        if faststart:
            cmd.extend(["-movflags", "+faststart"])
    else:
        # Re-encode fallback (more compatible but slow)
        cmd.extend([
            "-map", "0",
            "-c:v", "libx264", "-preset", reencode_video_preset, "-crf", str(reencode_crf),
            "-c:a", "aac", "-b:a", reencode_audio_bitrate,
        ])
        if convert_subtitles:
            cmd.extend(["-c:s", "mov_text"])
        else:
            cmd.extend(["-sn"])

    if overwrite:
        cmd.append("-y")

    if quiet:
        cmd.extend(["-loglevel", "error", "-nostats"])

    cmd.append(str(output_path))

    # ─── Run ffmpeg ─────────────────────────────────────────────────────────
    try:
        subprocess.run(
            cmd,
            check=True,
            capture_output=quiet,
            text=True,
        )
        print(f"Success → {output_path.name}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"Failed: {input_path.name}")
        if not quiet and e.stderr:
            print("ffmpeg error output:")
            print(e.stderr.strip())
        return False

    except FileNotFoundError:
        print("Error: ffmpeg not found.")
        print("Install ffmpeg → https://ffmpeg.org/download.html")
        print(" • Linux:   sudo apt install ffmpeg")
        print(" • macOS:   brew install ffmpeg")
        print(" • Windows: winget install -e --id Gyan.FFmpeg   or   chocolatey install ffmpeg")
        return False
