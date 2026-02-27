"""Pytest configuration for canvas-scraper smoke tests."""

import sys
from pathlib import Path

# Add src/ to path so tests can import the simple scripts
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
