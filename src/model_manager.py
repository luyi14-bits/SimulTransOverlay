"""Model download manager for ASR and translation models.

Handles automatic model downloading from HuggingFace.
Supports SHA256 verification, resume, progress callback, version management.
Models stored in %APPDATA%/SimulTransOverlay/models/ for cross-version sharing.
"""

import hashlib
import json
import logging
import os
import shutil
import sys
import threading
import time
from pathlib import Path
from typing import Callable, Dict, List, Optional

import requests

logger = logging.getLogger(__name__)

APP_NAME = "SimulTransOverlay"


def _get_appdata_dir() -> Path:
    """Get cross-version model storage directory.

    Uses %APPDATA%/SimulTransOverlay/models/ for Windows.
    Compatible with PyInstaller frozen exe.
    """
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path.home() / ".config"
    return base / APP_NAME / "models"


class DownloadProgress:
    """Tracks download progress for UI feedback."""

    def __init__(self, callback: Optional[Callable[[int, int], None]] = None):
        self.callback = callback
        self.last_update = 0.0

    def report(self, downloaded: int, total: int):
        now = time.time()
        if self.callback and now - self.last_update > 0.5:  # Throttle to 2 Hz
            self.callback(downloaded, total)
            self.last_update = now


class ModelManager:
    """Manage ASR and translation model downloads with integrity verification."""

    KNOWN_MODELS: Dict[str, Dict] = {
        # ASR models (faster-whisper)
        "faster-whisper-tiny": {
            "type": "asr",
            "hf_repo": "guillaumeklf/faster-whisper-tiny",
            "size_mb": 150,
            "sha256": "",
        },
        "faster-whisper-base": {
            "type": "asr",
            "hf_repo": "guillaumeklf/faster-whisper-base",
            "size_mb": 300,
            "sha256": "",
        },
        "faster-whisper-small": {
            "type": "asr",
            "hf_repo": "guillaumeklf/faster-whisper-small",
            "size_mb": 500,
            "sha256": "",
        },
        # Translation models (OPUS-MT ctranslate2 format - to be added)
    }

    def __init__(self, model_dir: Optional[Path] = None):
        self.model_dir = model_dir or _get_appdata_dir()
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self._manifest_path = self.model_dir / "manifest.json"
        self._lock = threading.Lock()
        self._manifest: Dict = self._load_manifest()

    # --- Manifest Management ---

    def _load_manifest(self) -> Dict:
        """Load manifest.json tracking downloaded models."""
        if self._manifest_path.exists():
            try:
                with open(self._manifest_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                logger.warning("Corrupted manifest, resetting")
        return {"version": 1, "models": {}}

    def _save_manifest(self):
        """Save manifest to disk."""
        with open(self._manifest_path, "w") as f:
            json.dump(self._manifest, f, indent=2)

    # --- Download with Integrity Verification ---

    def download(
        self,
        model_id: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> bool:
        """Download a model with SHA256 verification and resume support.

        Args:
            model_id: Model identifier (e.g., "faster-whisper-base")
            progress_callback: Called with (downloaded_bytes, total_bytes)

        Returns:
            True if download succeeded or model already cached
        """
        with self._lock:
            if self.is_downloaded(model_id):
                logger.info(f"Model '{model_id}' already cached")
                return True

            if model_id not in self.KNOWN_MODELS:
                logger.error(f"Unknown model: {model_id}")
                return False

            info = self.KNOWN_MODELS[model_id]
            model_path = self.model_dir / model_id
            model_path.mkdir(parents=True, exist_ok=True)

            logger.info(f"Downloading model '{model_id}' ({info['size_mb']}MB)...")

            try:
                if info["type"] == "asr":
                    self._download_asr_model(model_id, info, progress_callback)
                else:
                    logger.error(f"Unknown model type: {info['type']}")
                    return False

                # Verify integrity
                if info.get("sha256"):
                    if not self._verify_sha256(model_id, info["sha256"]):
                        logger.error(f"Model '{model_id}' SHA256 mismatch")
                        shutil.rmtree(model_path)
                        return False

                # Update manifest
                self._manifest["models"][model_id] = {
                    "downloaded_at": time.time(),
                    "size_mb": info["size_mb"],
                }
                self._save_manifest()

                logger.info(f"Model '{model_id}' downloaded successfully")
                return True

            except Exception as e:
                logger.error(f"Failed to download model '{model_id}': {e}")
                if model_path.exists():
                    shutil.rmtree(model_path)
                return False

    def _download_asr_model(
        self,
        model_id: str,
        info: Dict,
        progress_callback: Optional[Callable] = None,
    ):
        """Download faster-whisper model via huggingface_hub with progress."""
        try:
            from huggingface_hub import snapshot_download
            from huggingface_hub.utils import HfHubHTTPError

            progress = DownloadProgress(progress_callback)

            def _track_progress(current, total, _=None):
                progress.report(current, total)

            snapshot_download(
                repo_id=info["hf_repo"],
                local_dir=str(self.model_dir / model_id),
                local_dir_use_symlinks=False,
                resume_download=True,
                callback=_track_progress,
                ignore_patterns=["*.h5", "*.ot", "*.msgpack"],
            )
        except ImportError:
            logger.warning("huggingface_hub not installed, using direct download")
            self._download_direct(model_id, info, progress_callback)
        except HfHubHTTPError as e:
            logger.error(f"HuggingFace hub error: {e}")
            raise

    def _download_direct(
        self,
        model_id: str,
        info: Dict,
        progress_callback: Optional[Callable] = None,
    ):
        """Direct HTTP download fallback with resume support."""
        model_path = self.model_dir / model_id
        hf_base = f"https://huggingface.co/{info['hf_repo']}/resolve/main"

        # Download model files
        files_to_download = ["model.bin", "config.json", "tokenizer.json"]
        for filename in files_to_download:
            url = f"{hf_base}/{filename}"
            dest = model_path / filename
            self._download_file(url, dest, progress_callback)

    def _download_file(
        self,
        url: str,
        dest: Path,
        progress_callback: Optional[Callable] = None,
    ):
        """Download a single file with resume and progress."""
        temp_path = dest.with_suffix(".partial")
        headers = {}

        # Resume support: check if partial file exists
        if temp_path.exists():
            existing_size = temp_path.stat().st_size
            headers["Range"] = f"bytes={existing_size}-"
        else:
            existing_size = 0

        response = requests.get(url, headers=headers, stream=True, timeout=30)
        response.raise_for_status()

        total = int(response.headers.get("content-length", 0)) + existing_size
        progress = DownloadProgress(progress_callback)
        downloaded = existing_size

        mode = "ab" if existing_size > 0 else "wb"
        with open(temp_path, mode) as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    progress.report(downloaded, total)

        # Rename partial to final
        temp_path.rename(dest)

    # --- Verification ---

    def _verify_sha256(self, model_id: str, expected_sha: str) -> bool:
        """Verify model files integrity via SHA256."""
        model_path = self.model_dir / model_id
        if not model_path.exists():
            return False

        sha = hashlib.sha256()
        for fpath in sorted(model_path.rglob("*")):
            if fpath.is_file():
                sha.update(fpath.read_bytes())
        return sha.hexdigest() == expected_sha if expected_sha else True

    # --- Query ---

    def is_downloaded(self, model_id: str) -> bool:
        """Check if model is already downloaded."""
        return model_id in self._manifest.get("models", {})

    def get_model_path(self, model_id: str) -> Path:
        """Get local path for a downloaded model."""
        return self.model_dir / model_id

    def list_cached_models(self) -> List[str]:
        """List cached model IDs."""
        return list(self._manifest.get("models", {}).keys())

    def estimate_size(self, model_id: str) -> int:
        """Estimate download size in MB."""
        info = self.KNOWN_MODELS.get(model_id, {})
        return info.get("size_mb", 500)

    def clear_cache(self, model_id: Optional[str] = None) -> None:
        """Clear model cache."""
        with self._lock:
            if model_id:
                path = self.get_model_path(model_id)
                if path.exists():
                    shutil.rmtree(path)
                self._manifest["models"].pop(model_id, None)
            else:
                for cached in self.list_cached_models():
                    path = self.get_model_path(cached)
                    if path.exists():
                        shutil.rmtree(path)
                self._manifest["models"] = {}
            self._save_manifest()

    def total_cache_size_mb(self) -> int:
        """Calculate total size of all cached models."""
        total = 0
        for model_id in self.list_cached_models():
            total += self.estimate_size(model_id)
        return total
