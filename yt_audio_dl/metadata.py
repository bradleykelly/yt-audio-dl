"""Embed metadata tags into downloaded Opus files using mutagen."""

import re
from pathlib import Path

from mutagen.oggopus import OggOpus


# Patterns to strip from titles
_TITLE_NOISE = re.compile(
    r"\s*[\(\[]\s*(?:"
    r"Official\s+(?:Video|Audio|Music\s+Video|Lyric\s+Video|Visualizer)"
    r"|Lyric\s+Video"
    r"|Audio\s+Only"
    r"|Audio"
    r"|HQ"
    r"|HD"
    r"|4K"
    r")\s*[\)\]]",
    re.IGNORECASE,
)


def clean_title(title: str) -> str:
    """Strip common YouTube noise from a track title."""
    cleaned = _TITLE_NOISE.sub("", title)
    # Collapse multiple spaces
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    return cleaned or title


def get_artist(info: dict) -> str:
    """Extract the best artist name from info.json data."""
    for key in ("artist", "creator", "uploader", "channel"):
        val = info.get(key)
        if val:
            return val
    return "Unknown Artist"


def embed_metadata(
    opus_file: Path,
    info: dict,
    album: str,
    track_number: int,
    total_tracks: int,
    album_artist: str,
    artist_override: str | None = None,
    album_override: str | None = None,
) -> None:
    """Write tags to an Opus file using mutagen."""
    audio = OggOpus(opus_file)

    title = clean_title(info.get("title", opus_file.stem))
    artist = artist_override or get_artist(info)
    album_name = album_override or album

    audio["title"] = [title]
    audio["artist"] = [artist]
    audio["album"] = [album_name]
    audio["albumartist"] = [album_artist]
    audio["tracknumber"] = [str(track_number)]
    audio["tracktotal"] = [str(total_tracks)]

    upload_date = info.get("upload_date", "")
    if upload_date and len(upload_date) >= 4:
        audio["date"] = [upload_date[:4]]

    audio.save()


def determine_album_artist(infos: list[dict]) -> str:
    """Determine album artist: single artist if all same, else Various Artists."""
    artists = set()
    for info in infos:
        artists.add(get_artist(info))
    if len(artists) == 1:
        return artists.pop()
    return "Various Artists"
