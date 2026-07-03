"""pytest configuration for SimulTransOverlay."""

import sys
from pathlib import Path

# Add src/ to Python path so tests can import modules
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC_DIR))
