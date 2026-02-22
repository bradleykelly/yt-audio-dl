# yt-audio-dl

Download audio from YouTube playlists with metadata and Quod Libet integration.

## Install

```bash
sudo apt install -y yt-dlp ffmpeg
```

## Usage

```bash
# List tracks without downloading
python3 -m yt_audio_dl --dry-run "https://www.youtube.com/playlist?list=PLxxxxxx"

# Download playlist
python3 -m yt_audio_dl "https://www.youtube.com/playlist?list=PLxxxxxx"

# Custom output directory and album name
python3 -m yt_audio_dl -o ~/Music --album-name "My Album" "https://..."

# Skip Quod Libet registration
python3 -m yt_audio_dl --no-quodlibet "https://..."
```

## Options

| Flag | Description |
|------|-------------|
| `-o`, `--output-dir` | Base output directory (default: `~/Music`) |
| `--album-name` | Override album name |
| `--artist-name` | Override artist for all tracks |
| `--dry-run` | List tracks without downloading |
| `--no-quodlibet` | Skip Quod Libet integration |
| `-v`, `--verbose` | Show yt-dlp output |

## Output

Files are saved to `~/Music/<Artist>/<Album>/` as Opus with embedded metadata (title, artist, album, track number, album art).
