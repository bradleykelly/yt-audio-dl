"""Download audio from YouTube playlists using yt-dlp Python API."""

import json
import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yt_dlp


def normalize_playlist_url(url: str) -> str:
    """Normalize a YouTube URL to the canonical playlist format."""
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    list_id = qs.get("list", [None])[0]
    if list_id:
        return f"https://www.youtube.com/playlist?list={list_id}"
    return url


@dataclass
class PlaylistInfo:
    """Metadata extracted from a YouTube playlist."""

    title: str
    url: str
    entries: list[dict]
    uploader: str | None = None

    @property
    def track_count(self) -> int:
        return len(self.entries)


@dataclass
class DownloadResult:
    """Result of downloading a playlist."""

    playlist_info: PlaylistInfo
    downloaded_files: list[Path] = field(default_factory=list)
    info_json_files: list[Path] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def extract_playlist_info(url: str, verbose: bool = False) -> PlaylistInfo:
    """Extract playlist metadata without downloading."""
    url = normalize_playlist_url(url)
    opts = {
        "extract_flat": "in_playlist",
        "quiet": not verbose,
        "no_warnings": not verbose,
        "ignoreerrors": True,
    }
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)

    if info is None:
        raise RuntimeError("Failed to extract playlist info")

    # Materialize lazy iterator
    raw_entries = info.get("entries", []) or []
    raw_entries = list(raw_entries)

    entries = []
    for entry in raw_entries:
        if entry is not None:
            entries.append(
                {
                    "id": entry.get("id"),
                    "title": entry.get("title"),
                    "url": entry.get("url"),
                    "duration": entry.get("duration"),
                    "uploader": entry.get("uploader"),
                }
            )

    return PlaylistInfo(
        title=info.get("title", "Unknown Playlist"),
        url=url,
        entries=entries,
        uploader=info.get("uploader"),
    )


def download_playlist(
    url: str,
    temp_dir: Path | None = None,
    verbose: bool = False,
) -> DownloadResult:
    """Download all audio tracks from a playlist to a temp directory."""
    url = normalize_playlist_url(url)
    # First extract playlist info
    playlist_info = extract_playlist_info(url, verbose=verbose)

    if temp_dir is None:
        temp_dir = Path(tempfile.mkdtemp(prefix="yt-audio-dl-"))

    temp_dir.mkdir(parents=True, exist_ok=True)
    output_template = str(temp_dir / "%(playlist_index)03d - %(title)s.%(ext)s")

    opts = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "opus",
            },
            {
                "key": "FFmpegMetadata",
            },
            {
                "key": "EmbedThumbnail",
            },
        ],
        "writethumbnail": True,
        "writeinfojson": True,
        "outtmpl": output_template,
        "ignoreerrors": True,
        "quiet": not verbose,
        "no_warnings": not verbose,
        "noplaylist": False,
    }

    result = DownloadResult(playlist_info=playlist_info)

    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])

    # Collect downloaded files
    for path in sorted(temp_dir.iterdir()):
        if path.suffix == ".opus":
            result.downloaded_files.append(path)
        elif path.suffix == ".json" and path.stem.endswith(".info"):
            result.info_json_files.append(path)

    return result


def load_info_json(path: Path) -> dict:
    """Load and return the contents of an info.json file."""
    with open(path) as f:
        return json.load(f)
