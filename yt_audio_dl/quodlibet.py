"""Quod Libet integration: register downloaded albums with the music player."""

import shutil
import subprocess
import time
from pathlib import Path


def is_quodlibet_running() -> bool:
    """Check if Quod Libet is currently running."""
    try:
        result = subprocess.run(
            ["pgrep", "-x", "quodlibet"],
            capture_output=True,
        )
        return result.returncode == 0
    except FileNotFoundError:
        return False


def register_album(album_dir: Path, skip: bool = False) -> None:
    """Register an album directory with Quod Libet."""
    if skip:
        return

    if not shutil.which("quodlibet"):
        print("Quod Libet not found in PATH, skipping registration.")
        return

    if is_quodlibet_running():
        print("Registering album with Quod Libet...")
        subprocess.run(
            ["quodlibet", f"--add-location={album_dir}"],
            capture_output=True,
        )
        # Wait for the async library scan to finish before refreshing
        time.sleep(3)
        subprocess.run(
            ["quodlibet", "--refresh"],
            capture_output=True,
        )
        print("Album registered with Quod Libet.")
    else:
        print(
            "\nQuod Libet is not running. To add the album later, run:"
            f"\n  quodlibet --add-location={album_dir}"
            "\n  quodlibet --refresh"
        )
