"""
Water DRM module - handles license validation and session management.

Usage:
    from demo_game.drm import WaterDRM
    
    drm = WaterDRM(api_base="http://127.0.0.1:8000")
    
    # At game start
    if not drm.validate(launch_token, access_token):
        sys.exit("License validation failed")
    
    # During game loop (call periodically)
    drm.heartbeat()
    
    # At game end
    drm.close()
"""

import time
from dataclasses import dataclass
from typing import Callable

import httpx


@dataclass
class DRMConfig:
    """DRM configuration options."""
    api_base: str = "http://127.0.0.1:8080"
    heartbeat_interval: float = 30.0  # seconds
    request_timeout: float = 10.0
    allow_offline: bool = False  # If True, game can run without connection


class DRMError(Exception):
    """Raised when DRM validation fails."""
    pass


class WaterDRM:
    """
    Water DRM client for game integration.
    
    Handles:
    - Initial license validation (attest)
    - Periodic heartbeats to keep session alive
    - Graceful session closure
    """
    
    def __init__(
        self,
        config: DRMConfig | None = None,
        on_validation_failed: Callable[[str], None] | None = None,
    ):
        self.config = config or DRMConfig()
        self.on_validation_failed = on_validation_failed
        
        self._session_id: int | None = None
        self._access_token: str | None = None
        self._last_heartbeat: float = 0.0
        self._is_online: bool = False
        self._client = httpx.Client(timeout=self.config.request_timeout)
    
    @property
    def is_validated(self) -> bool:
        """Returns True if DRM validation succeeded."""
        return self._session_id is not None
    
    @property
    def is_online(self) -> bool:
        """Returns True if currently connected to server."""
        return self._is_online
    
    @property
    def session_id(self) -> int | None:
        """Returns current session ID if validated."""
        return self._session_id
    
    def _headers(self) -> dict[str, str]:
        """Build authorization headers."""
        if self._access_token:
            return {"Authorization": f"Bearer {self._access_token}"}
        return {}
    
    def validate(self, launch_token: str, access_token: str) -> bool:
        """
        Validate the launch token and establish a session.
        
        Args:
            launch_token: JWT token from /drm/launch endpoint
            access_token: User's access token for API auth
            
        Returns:
            True if validation succeeded, False otherwise
        """
        self._access_token = access_token
        
        try:
            response = self._client.post(
                f"{self.config.api_base}/sessions/attest",
                json={"token": launch_token},
                headers=self._headers(),
            )
            response.raise_for_status()
            
            data = response.json()
            self._session_id = data["session_id"]
            self._is_online = True
            self._last_heartbeat = time.time()
            
            return True
            
        except httpx.HTTPStatusError as e:
            error_msg = f"Validation failed: {e.response.status_code}"
            if e.response.status_code == 400:
                error_msg = "Invalid launch token"
            elif e.response.status_code == 401:
                error_msg = "Authentication failed"
            elif e.response.status_code == 403:
                error_msg = "No license for this game"
            
            if self.on_validation_failed:
                self.on_validation_failed(error_msg)
            
            if self.config.allow_offline:
                self._is_online = False
                return True
            return False
            
        except httpx.RequestError as e:
            error_msg = f"Connection failed: {e}"
            
            if self.on_validation_failed:
                self.on_validation_failed(error_msg)
            
            if self.config.allow_offline:
                self._is_online = False
                return True
            return False
    
    def heartbeat(self) -> bool:
        """
        Send heartbeat to keep session alive.
        
        Should be called periodically during game loop.
        Automatically rate-limits based on heartbeat_interval.
        
        Returns:
            True if heartbeat succeeded or not needed yet
        """
        if not self._session_id:
            return False
        
        now = time.time()
        if (now - self._last_heartbeat) < self.config.heartbeat_interval:
            return True  # Not time yet
        
        try:
            response = self._client.post(
                f"{self.config.api_base}/sessions/{self._session_id}/heartbeat",
                headers=self._headers(),
            )
            response.raise_for_status()
            
            self._last_heartbeat = now
            self._is_online = True
            return True
            
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            print(f"Heartbeat failed: {e}")
            self._is_online = False
            
            # If offline mode not allowed, this is fatal
            if not self.config.allow_offline:
                if self.on_validation_failed:
                    self.on_validation_failed("Lost connection to server")
                return False
            
            return True
    
    def close(self) -> None:
        """
        Close the DRM session gracefully.
        
        Should be called when game exits.
        """
        if self._session_id and self._is_online:
            try:
                # Send final heartbeat to mark clean exit
                self._client.post(
                    f"{self.config.api_base}/sessions/{self._session_id}/heartbeat",
                    headers=self._headers(),
                )
            except Exception:
                pass  # Best effort
        
        self._client.close()
        self._session_id = None
        self._is_online = False
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
