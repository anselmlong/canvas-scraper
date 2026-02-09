import os
import sys
import subprocess
import shutil
from pathlib import Path


def build():
    print("=" * 60)
    print("Canvas Scraper Standalone Executable Builder")
    print("=" * 60 + "\n")

    # Check if pyinstaller is installed
    try:
        subprocess.run(["pyinstaller", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # Set up paths
    project_root = Path(__file__).parent
    dist_dir = project_root / "dist"
    build_dir = project_root / "build"

    # Clean previous builds
    if dist_dir.exists():
        print(f"Cleaning {dist_dir}...")
        shutil.rmtree(dist_dir)
    if build_dir.exists():
        print(f"Cleaning {build_dir}...")
        shutil.rmtree(build_dir)

    # Determine separator for --add-data
    # Windows uses ;, others use :
    sep = ";" if os.name == "nt" else ":"

    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--noconfirm",
        "--onefile",
        "--console",
        "--name",
        "canvas-scraper",
        "--add-data",
        f"templates{sep}templates",
        "--add-data",
        f"config.example.yaml{sep}.",
        "src/main.py",
    ]

    print(f"Running: {' '.join(cmd)}")

    try:
        subprocess.check_call(cmd)

        executable_name = "canvas-scraper.exe" if os.name == "nt" else "canvas-scraper"
        executable_path = dist_dir / executable_name

        print("\n" + "=" * 60)
        print("SUCCESS!")
        print("=" * 60)
        print(f"Executable created at: {executable_path}")
        print("\nTo use it:")
        print(f"1. Copy {executable_name} to a new folder")
        print("2. Run it to start the setup wizard")
        print("=" * 60)

    except subprocess.CalledProcessError as e:
        print(f"\nBuild failed with exit code {e.returncode}")
        sys.exit(e.returncode)


if __name__ == "__main__":
    build()
