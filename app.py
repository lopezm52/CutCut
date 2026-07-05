import base64
import json
import os
import secrets
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

load_dotenv()

app = FastAPI(
    title="CutCut Audio Microservice",
    description="Split audio files and extract lightweight samples using ffmpeg.",
    version="1.1.0",
)

API_KEY = os.getenv("API_KEY", "default-api-key")
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "100"))
MAX_CHUNKS = int(os.getenv("MAX_CHUNKS", "50"))
FFMPEG_TIMEOUT_SECONDS = int(os.getenv("FFMPEG_TIMEOUT_SECONDS", "1800"))
UPLOAD_READ_SIZE = 1024 * 1024

SUPPORTED_FORMATS = {
    "mp3": "audio/mpeg",
    "wav": "audio/wav",
    "flac": "audio/flac",
    "aac": "audio/aac",
    "ogg": "audio/ogg",
    "m4a": "audio/mp4",
}

FFMPEG_FORMATS = {
    "mp3": "mp3",
    "wav": "wav",
    "flac": "flac",
    "aac": "adts",
    "ogg": "ogg",
    "m4a": "mp4",
}

FFMPEG_AUDIO_ARGS = {
    "mp3": ["-codec:a", "libmp3lame", "-b:a", "128k"],
    "wav": ["-codec:a", "pcm_s16le"],
    "flac": ["-codec:a", "flac"],
    "aac": ["-codec:a", "aac", "-b:a", "128k"],
    "ogg": ["-codec:a", "libvorbis", "-q:a", "4"],
    "m4a": ["-codec:a", "aac", "-b:a", "128k"],
}


def require_binary(binary: str) -> None:
    if shutil.which(binary) is None:
        raise RuntimeError(f"{binary} is not installed or not available in PATH")


require_binary("ffmpeg")
require_binary("ffprobe")


async def validate_api_key(
    x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
) -> Optional[str]:
    if not API_KEY:
        return x_api_key
    if not x_api_key or not secrets.compare_digest(x_api_key, API_KEY):
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return x_api_key


def parse_time_duration(value: str) -> int:
    duration = value.strip().lower()
    if not duration:
        raise ValueError("Duration cannot be empty")

    if duration.endswith("ms"):
        return int(float(duration[:-2]))
    if duration.endswith("s"):
        return int(float(duration[:-1]) * 1000)
    if duration.endswith("m"):
        return int(float(duration[:-1]) * 60 * 1000)
    if duration.endswith("h"):
        return int(float(duration[:-1]) * 60 * 60 * 1000)

    if ":" in duration:
        parts = [float(part) for part in duration.split(":")]
        if len(parts) == 3:
            hours, minutes, seconds = parts
            return int((hours * 3600 + minutes * 60 + seconds) * 1000)
        if len(parts) == 2:
            minutes, seconds = parts
            return int((minutes * 60 + seconds) * 1000)
        raise ValueError(f"Invalid duration format: {value}")

    try:
        return int(float(duration) * 1000)
    except ValueError as exc:
        raise ValueError(f"Invalid duration format: {value}") from exc


def parse_position(position: str, duration_ms: int, sample_ms: int) -> int:
    value = position.strip().lower()
    if value in {"middle", "mid", "center", "centre"}:
        return max(0, (duration_ms - sample_ms) // 2)
    if value in {"start", "beginning", "0"}:
        return 0
    if value == "end":
        return max(0, duration_ms - sample_ms)
    if value.endswith("%"):
        percent = float(value[:-1])
        if percent < 0 or percent > 100:
            raise ValueError("Percentage position must be between 0% and 100%")
        center_ms = int(duration_ms * (percent / 100))
        return max(0, min(center_ms - sample_ms // 2, duration_ms - sample_ms))
    return max(0, min(parse_time_duration(value), max(0, duration_ms - sample_ms)))


def get_mime_type(format_name: str) -> str:
    return SUPPORTED_FORMATS.get(format_name.lower(), "application/octet-stream")


def validate_format(format_name: str) -> str:
    normalized = format_name.lower().strip()
    if normalized not in SUPPORTED_FORMATS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format. Valid formats: {', '.join(SUPPORTED_FORMATS)}",
        )
    return normalized


async def save_upload_to_disk(upload: UploadFile, destination: Path) -> int:
    total = 0
    max_bytes = MAX_UPLOAD_MB * 1024 * 1024
    with destination.open("wb") as handle:
        while True:
            chunk = await upload.read(UPLOAD_READ_SIZE)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds MAX_UPLOAD_MB={MAX_UPLOAD_MB}",
                )
            handle.write(chunk)
    if total == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")
    return total


def run_command(command: List[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            command,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=FFMPEG_TIMEOUT_SECONDS,
        )
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or str(exc)).strip()
        raise HTTPException(status_code=400, detail=f"Audio processing failed: {detail}")
    except subprocess.TimeoutExpired as exc:
        raise HTTPException(
            status_code=504,
            detail=f"Audio processing timed out after {FFMPEG_TIMEOUT_SECONDS}s",
        ) from exc


def get_audio_info(file_path: Path) -> Dict[str, Any]:
    result = run_command(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration,size",
            "-of",
            "json",
            str(file_path),
        ]
    )
    payload = json.loads(result.stdout or "{}")
    info = payload.get("format") or {}
    duration_seconds = float(info.get("duration") or 0)
    if duration_seconds <= 0:
        raise HTTPException(status_code=400, detail="Could not determine audio duration")
    return {
        "duration_ms": int(duration_seconds * 1000),
        "size_bytes": int(float(info.get("size") or file_path.stat().st_size)),
    }


def build_ffmpeg_extract_command(
    input_path: Path,
    output_path: Path,
    start_ms: int,
    duration_ms: int,
    format_name: str,
) -> List[str]:
    return [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        f"{start_ms / 1000:.3f}",
        "-t",
        f"{duration_ms / 1000:.3f}",
        "-i",
        str(input_path),
        "-vn",
        "-map",
        "0:a:0",
        *FFMPEG_AUDIO_ARGS[format_name],
        "-f",
        FFMPEG_FORMATS[format_name],
        str(output_path),
    ]


def encode_file_base64(file_path: Path) -> str:
    with file_path.open("rb") as handle:
        return base64.b64encode(handle.read()).decode("utf-8")


def make_chunk(
    input_path: Path,
    output_dir: Path,
    index: int,
    start_ms: int,
    duration_ms: int,
    format_name: str,
) -> Dict[str, Any]:
    output_path = output_dir / f"chunk_{index:04d}.{format_name}"
    run_command(
        build_ffmpeg_extract_command(
            input_path=input_path,
            output_path=output_path,
            start_ms=start_ms,
            duration_ms=duration_ms,
            format_name=format_name,
        )
    )
    encoded = encode_file_base64(output_path)
    return {
        "index": index,
        "start_ms": start_ms,
        "end_ms": start_ms + duration_ms,
        "duration_ms": duration_ms,
        "format": format_name,
        "mime_type": get_mime_type(format_name),
        "base64": encoded,
        "data": encoded,
    }


def split_audio_sync(
    input_path: Path,
    chunk_ms: int,
    overlap_ms: int,
    format_name: str,
    original_filename: str,
    original_size_bytes: int,
) -> Dict[str, Any]:
    audio_info = get_audio_info(input_path)
    duration_ms = audio_info["duration_ms"]
    step_ms = chunk_ms - overlap_ms
    starts = list(range(0, duration_ms, step_ms))
    if len(starts) > MAX_CHUNKS:
        starts = starts[:MAX_CHUNKS]

    with tempfile.TemporaryDirectory(prefix="cutcut_chunks_") as output_dir_name:
        output_dir = Path(output_dir_name)
        chunks = []
        for index, start_ms in enumerate(starts):
            actual_duration_ms = min(chunk_ms, duration_ms - start_ms)
            if actual_duration_ms < 1000:
                continue
            chunks.append(
                make_chunk(
                    input_path=input_path,
                    output_dir=output_dir,
                    index=index,
                    start_ms=start_ms,
                    duration_ms=actual_duration_ms,
                    format_name=format_name,
                )
            )

    return {
        "filename": original_filename,
        "original_duration_ms": duration_ms,
        "original_size_bytes": original_size_bytes,
        "chunk_duration_ms": chunk_ms,
        "overlap_ms": overlap_ms,
        "overlap_duration_ms": overlap_ms,
        "total_chunks": len(chunks),
        "max_chunks": MAX_CHUNKS,
        "format": format_name,
        "output_format": format_name,
        "chunks": chunks,
    }


def sample_audio_sync(
    input_path: Path,
    sample_ms: int,
    position: str,
    format_name: str,
    original_filename: str,
    original_size_bytes: int,
) -> Dict[str, Any]:
    audio_info = get_audio_info(input_path)
    duration_ms = audio_info["duration_ms"]
    if sample_ms > duration_ms:
        sample_ms = duration_ms
    start_ms = parse_position(position, duration_ms, sample_ms)

    with tempfile.TemporaryDirectory(prefix="cutcut_sample_") as output_dir_name:
        output_dir = Path(output_dir_name)
        sample = make_chunk(
            input_path=input_path,
            output_dir=output_dir,
            index=0,
            start_ms=start_ms,
            duration_ms=sample_ms,
            format_name=format_name,
        )

    return {
        "filename": original_filename,
        "original_duration_ms": duration_ms,
        "original_size_bytes": original_size_bytes,
        "sample_position": position,
        "sample": sample,
    }


async def receive_upload(file: UploadFile) -> tuple[Path, tempfile.TemporaryDirectory, int]:
    suffix = Path(file.filename or "audio").suffix or ".audio"
    temp_dir = tempfile.TemporaryDirectory(prefix="cutcut_upload_")
    input_path = Path(temp_dir.name) / f"input{suffix}"
    try:
        size = await save_upload_to_disk(file, input_path)
        return input_path, temp_dir, size
    except Exception:
        temp_dir.cleanup()
        raise


@app.get("/")
async def root() -> Dict[str, Any]:
    return {
        "service": "CutCut Audio Microservice",
        "status": "healthy",
        "version": "1.1.0",
        "supported_formats": list(SUPPORTED_FORMATS.keys()),
        "endpoints": ["/split", "/sample", "/health"],
    }


@app.get("/health")
async def health() -> Dict[str, str]:
    return {"status": "healthy"}


@app.post("/split")
async def split_audio(
    file: UploadFile = File(...),
    chunk: str = Query(..., description="Chunk duration, e.g. 300s, 5m, 00:05:00, 300000ms"),
    overlap: str = Query("5s", description="Overlap between chunks"),
    format: str = Query("mp3", description="Output format: mp3, wav, flac, aac, ogg, m4a"),
    api_key: Optional[str] = Depends(validate_api_key),
) -> JSONResponse:
    format_name = validate_format(format)
    try:
        chunk_ms = parse_time_duration(chunk)
        overlap_ms = parse_time_duration(overlap)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if chunk_ms < 1000:
        raise HTTPException(status_code=400, detail="Chunk duration must be at least 1 second")
    if overlap_ms >= chunk_ms:
        raise HTTPException(status_code=400, detail="Overlap must be smaller than chunk duration")

    input_path, temp_dir, size = await receive_upload(file)
    try:
        result = await run_in_threadpool(
            split_audio_sync,
            input_path,
            chunk_ms,
            overlap_ms,
            format_name,
            file.filename or "audio",
            size,
        )
        return JSONResponse(content=result)
    finally:
        temp_dir.cleanup()


@app.post("/sample")
async def sample_audio(
    file: UploadFile = File(...),
    duration: str = Query("30s", description="Sample duration"),
    position: str = Query("50%", description="start, middle, end, 50%, or timestamp like 10m"),
    format: str = Query("mp3", description="Output format: mp3, wav, flac, aac, ogg, m4a"),
    api_key: Optional[str] = Depends(validate_api_key),
) -> JSONResponse:
    format_name = validate_format(format)
    try:
        sample_ms = parse_time_duration(duration)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if sample_ms < 1000:
        raise HTTPException(status_code=400, detail="Sample duration must be at least 1 second")

    input_path, temp_dir, size = await receive_upload(file)
    try:
        result = await run_in_threadpool(
            sample_audio_sync,
            input_path,
            sample_ms,
            position,
            format_name,
            file.filename or "audio",
            size,
        )
        return JSONResponse(content=result)
    finally:
        temp_dir.cleanup()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=3000)
