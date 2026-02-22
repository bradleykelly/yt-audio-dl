"""CLI entry point: python3 -m yt_audio_dl <playlist-url>."""

import argparse
import json
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path

from .downloader import (
    DownloadResult,
    download_playlist,
    extract_playlist_info,
    load_info_json,
)
from .metadata import (
    clean_title,
    determine_album_artist,
    embed_metadata,
    get_artist,
)
from .quodlibet import register_album


def sanitize_filename(name: str) -> str:
    """Strip illegal characters and collapse whitespace."""
    name = re.sub(r'[<>:"/\\|?*]', "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:200]


def check_dependencies() -> None:
    """Verify required external tools are available."""
    missing = []
    for cmd in ("yt-dlp", "ffmpeg"):
        if not shutil.which(cmd):
            missing.append(cmd)
    if missing:
        print(f"Error: missing required tools: {', '.join(missing)}", file=sys.stderr)
        print("Install with: sudo apt install -y yt-dlp ffmpeg", file=sys.stderr)
        sys.exit(1)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="yt-audio-dl",
        description="Download audio from a YouTube playlist with metadata.",
    )
    parser.add_argument("url", help="YouTube playlist URL")
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path.home() / "Music",
        help="Base output directory (default: ~/Music)",
    )
    parser.add_argument("--album-name", help="Override album name")
    parser.add_argument("--artist-name", help="Override artist for all tracks")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List tracks without downloading",
    )
    parser.add_argument(
        "--no-quodlibet",
        action="store_true",
        help="Skip Quod Libet integration",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show yt-dlp output",
    )
    return parser.parse_args(argv)


def dry_run(url: str, verbose: bool = False) -> None:
    """Print playlist info without downloading."""
    info = extract_playlist_info(url, verbose=verbose)
    print(f"\nPlaylist: {info.title}")
    print(f"Tracks:   {info.track_count}")
    if info.uploader:
        print(f"Uploader: {info.uploader}")
    print()
    for i, entry in enumerate(info.entries, 1):
        duration = entry.get("duration")
        dur_str = f" [{duration // 60}:{duration % 60:02d}]" if duration else ""
        print(f"  {i:3d}. {entry['title']}{dur_str}")
    print()


def move_and_tag(
    result: DownloadResult,
    output_dir: Path,
    album_override: str | None,
    artist_override: str | None,
) -> Path:
    """Embed metadata and move files to the final album directory."""
    # Load all info.json files and pair with opus files
    pairs: list[tuple[Path, dict]] = []
    info_map: dict[str, dict] = {}

    for info_path in result.info_json_files:
        info = load_info_json(info_path)
        # Key is the stem without .info suffix
        stem = info_path.name.removesuffix(".info.json")
        info_map[stem] = info

    for opus_file in result.downloaded_files:
        stem = opus_file.stem
        info = info_map.get(stem, {})
        pairs.append((opus_file, info))

    if not pairs:
        print("No tracks were downloaded.", file=sys.stderr)
        sys.exit(1)

    # Determine album metadata
    all_infos = [info for _, info in pairs]
    album_name = album_override or result.playlist_info.title
    album_artist = (
        artist_override
        if artist_override
        else determine_album_artist(all_infos)
    )

    # Build destination directory
    safe_artist = sanitize_filename(album_artist)
    safe_album = sanitize_filename(album_name)
    album_dir = output_dir / safe_artist / safe_album
    album_dir.mkdir(parents=True, exist_ok=True)

    log_entries = []

    for i, (opus_file, info) in enumerate(pairs, 1):
        # Tag the file
        embed_metadata(
            opus_file=opus_file,
            info=info,
            album=album_name,
            track_number=i,
            total_tracks=len(pairs),
            album_artist=album_artist,
            artist_override=artist_override,
        )

        # Build clean filename
        title = clean_title(info.get("title", opus_file.stem))
        safe_title = sanitize_filename(title)
        dest_name = f"{i:02d} - {safe_title}.opus"
        dest_path = album_dir / dest_name

        shutil.move(str(opus_file), str(dest_path))

        log_entries.append(
            {
                "track_number": i,
                "video_id": info.get("id", ""),
                "title": title,
                "artist": artist_override or get_artist(info),
                "filename": dest_name,
                "duration": info.get("duration"),
            }
        )

        print(f"  {dest_name}")

    # Write download log
    log = {
        "playlist_url": result.playlist_info.url,
        "playlist_title": result.playlist_info.title,
        "album": album_name,
        "album_artist": album_artist,
        "download_date": datetime.now(timezone.utc).isoformat(),
        "tracks": log_entries,
        "errors": result.errors,
    }
    log_path = album_dir / "download_log.json"
    with open(log_path, "w") as f:
        json.dump(log, f, indent=2)

    return album_dir


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    check_dependencies()

    if args.dry_run:
        dry_run(args.url, verbose=args.verbose)
        return

    print(f"Extracting playlist info...")
    result = download_playlist(args.url, verbose=args.verbose)

    print(
        f"\nDownloaded {len(result.downloaded_files)} tracks "
        f"from '{result.playlist_info.title}'"
    )

    if not result.downloaded_files:
        print("No tracks downloaded.", file=sys.stderr)
        sys.exit(1)

    print("\nTagging and organizing files...")
    album_dir = move_and_tag(
        result,
        output_dir=args.output_dir,
        album_override=args.album_name,
        artist_override=args.artist_name,
    )

    print(f"\nAlbum saved to: {album_dir}")

    register_album(album_dir, skip=args.no_quodlibet)

    print("\nDone!")


if __name__ == "__main__":
    main()
