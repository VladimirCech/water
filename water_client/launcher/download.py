"""
Download manager for Water Launcher.

Handles downloading game builds from the server with progress tracking.
"""

import hashlib
import logging
from pathlib import Path
from typing import Callable, Optional

import httpx

from .config import GAMES_DIR

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("water.download")


class DownloadError(Exception):
    """Raised when download fails."""
    pass


class DownloadManager:
    """Manages game downloads with progress tracking."""

    def __init__(self):
        self._client = httpx.Client(timeout=300.0, follow_redirects=True)
        GAMES_DIR.mkdir(parents=True, exist_ok=True)

    def get_game_path(self, game_slug: str, version: str) -> Path:
        """Get the local path for a game build."""
        return GAMES_DIR / game_slug / version

    def is_installed(self, game_slug: str, version: str) -> bool:
        """Check if a game version is already downloaded."""
        game_path = self.get_game_path(game_slug, version)
        return game_path.exists() and (game_path / "game.zip").exists()

    def get_installed_versions(self, game_slug: str) -> list[str]:
        """Get list of installed versions for a game."""
        game_dir = GAMES_DIR / game_slug
        if not game_dir.exists():
            return []
        return [d.name for d in game_dir.iterdir() if d.is_dir() and (d / "game.zip").exists()]

    def download(
        self,
        url: str,
        game_slug: str,
        version: str,
        expected_sha256: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Path:
        """
        Download a game build.

        Args:
            url: Presigned download URL
            game_slug: Game slug for directory naming
            version: Build version
            expected_sha256: Expected SHA256 hash for verification
            progress_callback: Callback(downloaded_bytes, total_bytes)

        Returns:
            Path to downloaded game directory
        """
        logger.info(f"Starting download for {game_slug} v{version}")
        logger.debug(f"Download URL: {url}")
        
        # Fix MinIO URL if it uses internal Docker hostname
        if "://minio:" in url:
            url = url.replace("://minio:", "://localhost:")
            logger.info(f"Fixed MinIO URL to use localhost: {url}")
        
        game_path = self.get_game_path(game_slug, version)
        game_path.mkdir(parents=True, exist_ok=True)
        
        zip_path = game_path / "game.zip"
        logger.debug(f"Saving to: {zip_path}")

        # Download with streaming
        try:
            logger.info("Starting HTTP download...")
            with self._client.stream("GET", url) as response:
                response.raise_for_status()
                
                total_size = int(response.headers.get("content-length", 0))
                logger.info(f"Download size: {total_size} bytes")
                downloaded = 0
                sha256_hash = hashlib.sha256()

                with open(zip_path, "wb") as f:
                    for chunk in response.iter_bytes(chunk_size=8192):
                        f.write(chunk)
                        sha256_hash.update(chunk)
                        downloaded += len(chunk)
                        
                        if progress_callback:
                            progress_callback(downloaded, total_size)
                
                logger.info(f"Download complete: {downloaded} bytes")

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e.response.status_code}")
            # Clean up partial download
            if zip_path.exists():
                zip_path.unlink()
            raise DownloadError(f"Download failed: HTTP {e.response.status_code}")
        except Exception as e:
            logger.error(f"Download error: {e}")
            if zip_path.exists():
                zip_path.unlink()
            raise DownloadError(f"Download failed: {e}")

        # Verify hash if provided
        if expected_sha256:
            actual_hash = sha256_hash.hexdigest()
            if actual_hash != expected_sha256:
                zip_path.unlink()
                raise DownloadError(
                    f"Hash mismatch! Expected {expected_sha256[:16]}..., got {actual_hash[:16]}..."
                )

        return game_path

    def delete_game(self, game_slug: str, version: Optional[str] = None) -> bool:
        """
        Delete a downloaded game.

        Args:
            game_slug: Game slug
            version: Specific version to delete, or None for all versions

        Returns:
            True if deleted successfully
        """
        import shutil

        if version:
            game_path = self.get_game_path(game_slug, version)
            if game_path.exists():
                shutil.rmtree(game_path)
                return True
        else:
            game_dir = GAMES_DIR / game_slug
            if game_dir.exists():
                shutil.rmtree(game_dir)
                return True

        return False
