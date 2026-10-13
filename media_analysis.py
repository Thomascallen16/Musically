"""Native media inspection helpers for Musically."""
from pathlib import Path
from urllib.parse import urlparse
import shutil
import subprocess
import json


def media_kind(url: str, content_type: str = "") -> str:
    mime = (content_type or "").split(";", 1)[0].strip().lower()
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix == ".m3u8" or mime in {"application/vnd.apple.mpegurl", "application/x-mpegurl", "audio/mpegurl"}:
        return "hls_manifest"
    if suffix == ".mpd" or mime == "application/dash+xml":
        return "dash_manifest"
    if mime.startswith("audio/") or suffix in {".mp3", ".m4a", ".aac", ".wav", ".flac", ".ogg", ".opus", ".webm", ".mp4", ".m4s", ".ts"}:
        return "direct_media"
    return "unknown"


def candidate_score(item: dict) -> tuple:
    kind = media_kind(str(item.get("url", "")), str(item.get("content_type", "")))
    kind_score = {"hls_manifest": 4, "dash_manifest": 4, "direct_media": 3, "unknown": 0}.get(kind, 0)
    status = int(item.get("status", 0) or 0)
    return (1 if 200 <= status < 300 else 0, kind_score,
            int(item.get("length", 0) or 0), float(item.get("time", 0) or 0))


def choose_candidate(items: list[dict]) -> dict | None:
    return max(items, key=candidate_score) if items else None


def inspect_hls_manifest(text: str) -> dict:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not any(line == "#EXTM3U" for line in lines[:3]):
        return {"valid": False, "kind": "hls", "error": "Missing #EXTM3U header"}
    return {
        "valid": True,
        "kind": "hls",
        "variants": sum(line.startswith("#EXT-X-STREAM-INF:") for line in lines),
        "segments": sum(not line.startswith("#") for line in lines),
        "encrypted_or_keyed": any(line.startswith("#EXT-X-KEY:") and "METHOD=NONE" not in line for line in lines),
    }


def inspect_dash_manifest(text: str) -> dict:
    import xml.etree.ElementTree as ET
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        return {"valid": False, "kind": "dash", "error": f"Invalid XML: {exc}"}
    if root.tag.rsplit("}", 1)[-1] != "MPD":
        return {"valid": False, "kind": "dash", "error": "Root element is not MPD"}
    nodes = list(root.iter())
    adaptations = [n for n in nodes if n.tag.rsplit("}", 1)[-1] == "AdaptationSet"]
    representations = [n for n in nodes if n.tag.rsplit("}", 1)[-1] == "Representation"]
    return {
        "valid": True, "kind": "dash", "adaptation_sets": len(adaptations),
        "representations": len(representations),
        "content_types": sorted({n.attrib["contentType"].lower() for n in adaptations if n.attrib.get("contentType")}),
        "protected": any(n.tag.rsplit("}", 1)[-1] == "ContentProtection" for n in nodes),
    }


def inspect_file(path: Path, root: Path | None = None, timeout: int = 30) -> dict:
    path = Path(path)
    if not path.is_file():
        return {"valid": False, "error": "File does not exist"}
    size = path.stat().st_size
    if size == 0:
        return {"valid": False, "size_bytes": 0, "error": "File is empty"}
    probe = None
    if root:
        for name in ("ffprobe.exe", "ffprobe"):
            candidate = root / name
            if candidate.is_file():
                probe = str(candidate)
                break
    probe = probe or shutil.which("ffprobe")
    if not probe:
        return {"valid": None, "size_bytes": size, "error": "FFprobe unavailable; only file presence and size checked"}
    cmd = [probe, "-v", "error", "-show_entries",
           "format=format_name,duration,bit_rate:stream=index,codec_type,codec_name,sample_rate,channels,width,height,bit_rate",
           "-of", "json", str(path)]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"valid": False, "size_bytes": size, "error": str(exc)}
    if result.returncode:
        return {"valid": False, "size_bytes": size, "error": result.stderr.strip() or "FFprobe could not read media"}
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return {"valid": False, "size_bytes": size, "error": "FFprobe returned invalid JSON"}
    streams = data.get("streams", [])
    return {"valid": bool(streams), "size_bytes": size, "format": data.get("format", {}),
            "streams": streams, "has_audio": any(s.get("codec_type") == "audio" for s in streams),
            "has_video": any(s.get("codec_type") == "video" for s in streams)}
