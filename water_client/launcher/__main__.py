"""
Water Launcher - Desktop client for Water game store.

A PySide6-based game launcher that handles:
- User authentication (login/register)
- Game library browsing
- Store browsing and purchases
- Game downloads and launching
"""

import subprocess
import sys
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QLineEdit,
    QDialog,
    QFormLayout,
    QTabWidget,
    QProgressDialog,
    QTextEdit,
    QSplitter,
    QGroupBox,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
import httpx

from .config import API_BASE, GAMES_DIR
from .download import DownloadManager, DownloadError


class DownloadThread(QThread):
    """Background thread for downloading games."""

    progress = Signal(int, int)  # downloaded, total
    finished = Signal(Path)  # game_path
    error = Signal(str)  # error message

    def __init__(
        self,
        download_manager: DownloadManager,
        url: str,
        game_slug: str,
        version: str,
        expected_sha256: Optional[str] = None,
    ):
        super().__init__()
        self.dm = download_manager
        self.url = url
        self.game_slug = game_slug
        self.version = version
        self.expected_sha256 = expected_sha256

    def run(self):
        try:
            game_path = self.dm.download(
                self.url,
                self.game_slug,
                self.version,
                self.expected_sha256,
                progress_callback=lambda d, t: self.progress.emit(d, t),
            )
            self.finished.emit(game_path)
        except DownloadError as e:
            self.error.emit(str(e))
        except Exception as e:
            self.error.emit(f"Unexpected error: {e}")


class ApiClient:
    """HTTP client for Water API."""

    def __init__(self):
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.username: Optional[str] = None
        self._client = httpx.Client(timeout=30.0)

    def _headers(self) -> dict:
        if self.access_token:
            return {"Authorization": f"Bearer {self.access_token}"}
        return {}

    def login(self, username: str, password: str) -> dict:
        """Login and store tokens."""
        resp = self._client.post(
            f"{API_BASE}/auth/login",
            json={"username": username, "password": password},
        )
        resp.raise_for_status()
        data = resp.json()
        self.access_token = data["access_token"]
        self.refresh_token = data["refresh_token"]
        self.username = username
        return data

    def register(self, username: str, email: str, password: str) -> dict:
        """Register new user."""
        resp = self._client.post(
            f"{API_BASE}/auth/register",
            json={"username": username, "email": email, "password": password},
        )
        resp.raise_for_status()
        data = resp.json()
        self.access_token = data["access_token"]
        self.refresh_token = data["refresh_token"]
        self.username = username
        return data

    def refresh(self) -> bool:
        """Refresh access token."""
        if not self.refresh_token:
            return False
        try:
            resp = self._client.post(
                f"{API_BASE}/auth/refresh",
                json={"refresh_token": self.refresh_token},
            )
            resp.raise_for_status()
            data = resp.json()
            self.access_token = data["access_token"]
            self.refresh_token = data["refresh_token"]
            return True
        except Exception:
            return False

    def get_library(self) -> list[dict]:
        """Get user's owned games."""
        resp = self._client.get(f"{API_BASE}/games/", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    def get_store(self) -> list[dict]:
        """Get all games in store."""
        resp = self._client.get(f"{API_BASE}/shop/", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    def purchase(self, game_id: int) -> dict:
        """Purchase a game."""
        resp = self._client.post(
            f"{API_BASE}/shop/purchase/{game_id}",
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def get_builds(self, game_id: int) -> list[dict]:
        """Get builds for a game."""
        resp = self._client.get(
            f"{API_BASE}/games/{game_id}/builds",
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def get_launch_token(self, build_id: int) -> str:
        """Get DRM launch token."""
        resp = self._client.post(
            f"{API_BASE}/launch/{build_id}",
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()["token"]

    def get_download_url(self, build_id: int) -> str:
        """Get presigned download URL for a build."""
        resp = self._client.get(
            f"{API_BASE}/games/builds/{build_id}/download",
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()["url"]

    def logout(self):
        """Clear tokens."""
        self.access_token = None
        self.refresh_token = None
        self.username = None


class LoginDialog(QDialog):
    """Login/Register dialog."""

    def __init__(self, api: ApiClient, parent=None):
        super().__init__(parent)
        self.api = api
        self.setWindowTitle("Water - Login")
        self.setMinimumWidth(350)

        layout = QVBoxLayout(self)

        # Tabs for login/register
        tabs = QTabWidget()
        layout.addWidget(tabs)

        # Login tab
        login_widget = QWidget()
        login_layout = QFormLayout(login_widget)
        self.login_username = QLineEdit()
        self.login_password = QLineEdit()
        self.login_password.setEchoMode(QLineEdit.Password)
        login_layout.addRow("Username:", self.login_username)
        login_layout.addRow("Password:", self.login_password)
        login_btn = QPushButton("Login")
        login_btn.clicked.connect(self._do_login)
        login_layout.addRow(login_btn)
        tabs.addTab(login_widget, "Login")

        # Register tab
        register_widget = QWidget()
        register_layout = QFormLayout(register_widget)
        self.reg_username = QLineEdit()
        self.reg_email = QLineEdit()
        self.reg_password = QLineEdit()
        self.reg_password.setEchoMode(QLineEdit.Password)
        self.reg_password2 = QLineEdit()
        self.reg_password2.setEchoMode(QLineEdit.Password)
        register_layout.addRow("Username:", self.reg_username)
        register_layout.addRow("Email:", self.reg_email)
        register_layout.addRow("Password:", self.reg_password)
        register_layout.addRow("Confirm:", self.reg_password2)
        register_btn = QPushButton("Register")
        register_btn.clicked.connect(self._do_register)
        register_layout.addRow(register_btn)
        tabs.addTab(register_widget, "Register")

        # Status label
        self.status = QLabel("")
        self.status.setStyleSheet("color: red;")
        layout.addWidget(self.status)

    def _do_login(self):
        try:
            self.api.login(
                self.login_username.text().strip(),
                self.login_password.text(),
            )
            self.accept()
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                self.status.setText("Invalid username or password")
            else:
                self.status.setText(f"Error: {e.response.text}")
        except Exception as e:
            self.status.setText(f"Connection error: {e}")

    def _do_register(self):
        if self.reg_password.text() != self.reg_password2.text():
            self.status.setText("Passwords don't match")
            return

        try:
            self.api.register(
                self.reg_username.text().strip(),
                self.reg_email.text().strip(),
                self.reg_password.text(),
            )
            self.accept()
        except httpx.HTTPStatusError as e:
            try:
                detail = e.response.json().get("detail", str(e))
            except Exception:
                detail = e.response.text
            self.status.setText(f"Error: {detail}")
        except Exception as e:
            self.status.setText(f"Connection error: {e}")


class GameListItem(QListWidgetItem):
    """Custom list item for games."""

    def __init__(self, game: dict, installed: bool = False, in_library: bool = True):
        self.game = game
        self.installed = installed
        owned = game.get("owned", True)  # Library items are always owned
        price = game.get("price", "0.00")

        if in_library:
            # Library view - show installed status
            if installed:
                text = f"✅ {game['name']} [Installed]"
            else:
                text = f"⬇️ {game['name']} [Not installed]"
        else:
            # Store view - show owned/price
            if owned:
                text = f"✓ {game['name']} [Owned]"
            else:
                text = f"{game['name']} - ${price}"

        super().__init__(text)

        if in_library:
            if installed:
                self.setForeground(Qt.darkGreen)
            else:
                self.setForeground(Qt.darkGray)
        elif owned:
            self.setForeground(Qt.darkGreen)


class MainWindow(QMainWindow):
    """Main launcher window."""

    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self.download_manager = DownloadManager()
        self.setWindowTitle("Water Launcher")
        self.setMinimumSize(800, 500)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Header
        header = QHBoxLayout()
        title = QLabel("💧 Water")
        title.setFont(QFont("Arial", 24, QFont.Bold))
        header.addWidget(title)
        header.addStretch()

        self.user_label = QLabel("Not logged in")
        header.addWidget(self.user_label)

        self.logout_btn = QPushButton("Logout")
        self.logout_btn.clicked.connect(self._logout)
        self.logout_btn.setVisible(False)
        header.addWidget(self.logout_btn)

        layout.addLayout(header)

        # Tabs
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Library tab
        library_widget = QWidget()
        library_layout = QVBoxLayout(library_widget)
        
        # Splitter for list and details
        library_splitter = QSplitter(Qt.Horizontal)
        
        # Left side - game list
        library_left = QWidget()
        library_left_layout = QVBoxLayout(library_left)
        library_left_layout.setContentsMargins(0, 0, 0, 0)
        self.library_list = QListWidget()
        self.library_list.itemDoubleClicked.connect(self._play_game)
        library_left_layout.addWidget(QLabel("Your Games:"))
        library_left_layout.addWidget(self.library_list)
        library_splitter.addWidget(library_left)
        
        # Right side - game details
        library_details = QGroupBox("Game Details")
        library_details_layout = QVBoxLayout(library_details)
        self.library_title = QLabel("Select a game")
        self.library_title.setFont(QFont("Arial", 16, QFont.Bold))
        self.library_desc = QTextEdit()
        self.library_desc.setReadOnly(True)
        self.library_desc.setPlaceholderText("Select a game to see its description")
        library_details_layout.addWidget(self.library_title)
        library_details_layout.addWidget(self.library_desc)
        library_splitter.addWidget(library_details)
        
        library_splitter.setSizes([250, 350])
        library_layout.addWidget(library_splitter)

        btn_layout = QHBoxLayout()
        self.play_btn = QPushButton("▶ Play")
        self.play_btn.clicked.connect(self._play_game)
        self.play_btn.setEnabled(False)
        btn_layout.addWidget(self.play_btn)
        
        self.uninstall_btn = QPushButton("🗑 Uninstall")
        self.uninstall_btn.clicked.connect(self._uninstall_game)
        self.uninstall_btn.setEnabled(False)
        btn_layout.addWidget(self.uninstall_btn)
        
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self._load_library)
        btn_layout.addWidget(self.refresh_btn)
        library_layout.addLayout(btn_layout)

        self.tabs.addTab(library_widget, "📚 Library")

        # Store tab
        store_widget = QWidget()
        store_layout = QVBoxLayout(store_widget)
        
        # Splitter for list and details
        store_splitter = QSplitter(Qt.Horizontal)
        
        # Left side - game list
        store_left = QWidget()
        store_left_layout = QVBoxLayout(store_left)
        store_left_layout.setContentsMargins(0, 0, 0, 0)
        self.store_list = QListWidget()
        self.store_list.itemSelectionChanged.connect(self._store_selection_changed)
        store_left_layout.addWidget(QLabel("Available Games:"))
        store_left_layout.addWidget(self.store_list)
        store_splitter.addWidget(store_left)
        
        # Right side - game details
        store_details = QGroupBox("Game Details")
        store_details_layout = QVBoxLayout(store_details)
        self.store_title = QLabel("Select a game")
        self.store_title.setFont(QFont("Arial", 16, QFont.Bold))
        self.store_price = QLabel("")
        self.store_price.setFont(QFont("Arial", 14))
        self.store_desc = QTextEdit()
        self.store_desc.setReadOnly(True)
        self.store_desc.setPlaceholderText("Select a game to see its description")
        store_details_layout.addWidget(self.store_title)
        store_details_layout.addWidget(self.store_price)
        store_details_layout.addWidget(self.store_desc)
        store_splitter.addWidget(store_details)
        
        store_splitter.setSizes([250, 350])
        store_layout.addWidget(store_splitter)

        store_btn_layout = QHBoxLayout()
        self.buy_btn = QPushButton("🛒 Purchase")
        self.buy_btn.clicked.connect(self._purchase_game)
        self.buy_btn.setEnabled(False)
        store_btn_layout.addWidget(self.buy_btn)
        self.store_refresh_btn = QPushButton("🔄 Refresh")
        self.store_refresh_btn.clicked.connect(self._load_store)
        store_btn_layout.addWidget(self.store_refresh_btn)
        store_layout.addLayout(store_btn_layout)

        self.tabs.addTab(store_widget, "🏪 Store")

        # Status bar
        self.statusBar().showMessage("Ready")

        # Connect signals
        self.library_list.itemSelectionChanged.connect(self._library_selection_changed)

        # Show login if not authenticated
        if not self.api.access_token:
            self._show_login()
        else:
            self._on_logged_in()

    def _show_login(self):
        dialog = LoginDialog(self.api, self)
        if dialog.exec() == QDialog.Accepted:
            self._on_logged_in()
        else:
            # Exit if login cancelled
            QApplication.quit()

    def _on_logged_in(self):
        self.user_label.setText(f"👤 {self.api.username}")
        self.logout_btn.setVisible(True)
        self._load_library()
        self._load_store()

    def _logout(self):
        self.api.logout()
        self.user_label.setText("Not logged in")
        self.logout_btn.setVisible(False)
        self.library_list.clear()
        self.store_list.clear()
        self._show_login()

    def _load_library(self):
        try:
            games = self.api.get_library()
            self.library_list.clear()
            for game in games:
                # Check if any version is installed
                installed_versions = self.download_manager.get_installed_versions(game["slug"])
                is_installed = len(installed_versions) > 0
                self.library_list.addItem(GameListItem(game, installed=is_installed, in_library=True))
            self.statusBar().showMessage(f"Loaded {len(games)} games")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load library: {e}")

    def _load_store(self):
        try:
            games = self.api.get_store()
            self.store_list.clear()
            for game in games:
                self.store_list.addItem(GameListItem(game, installed=False, in_library=False))
            self.statusBar().showMessage(f"Loaded {len(games)} games from store")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load store: {e}")

    def _library_selection_changed(self):
        items = self.library_list.selectedItems()
        has_selection = len(items) == 1
        
        # Update details panel and buttons
        if has_selection:
            item = items[0]
            if isinstance(item, GameListItem):
                game = item.game
                self.library_title.setText(game["name"])
                self.library_desc.setText(game.get("description", "No description available."))
                
                # Change button text based on installed status
                if item.installed:
                    self.play_btn.setText("▶ Play")
                    self.play_btn.setEnabled(True)
                    self.uninstall_btn.setEnabled(True)
                else:
                    self.play_btn.setText("⬇ Install")
                    self.play_btn.setEnabled(True)
                    self.uninstall_btn.setEnabled(False)
            else:
                self.play_btn.setEnabled(False)
                self.uninstall_btn.setEnabled(False)
        else:
            self.library_title.setText("Select a game")
            self.library_desc.clear()
            self.play_btn.setText("▶ Play")
            self.play_btn.setEnabled(False)
            self.uninstall_btn.setEnabled(False)

    def _store_selection_changed(self):
        items = self.store_list.selectedItems()
        if items:
            item = items[0]
            if isinstance(item, GameListItem):
                game = item.game
                # Update details panel
                self.store_title.setText(game["name"])
                price = game.get("price", "0.00")
                owned = game.get("owned", False)
                if owned:
                    self.store_price.setText("✓ Owned")
                    self.store_price.setStyleSheet("color: green; font-weight: bold;")
                else:
                    self.store_price.setText(f"${price}")
                    self.store_price.setStyleSheet("color: #4285f4; font-weight: bold;")
                self.store_desc.setText(game.get("description", "No description available."))
                # Enable buy only if not owned
                self.buy_btn.setEnabled(not owned)
            else:
                self.buy_btn.setEnabled(False)
        else:
            self.store_title.setText("Select a game")
            self.store_price.setText("")
            self.store_desc.clear()
            self.buy_btn.setEnabled(False)

    def _play_game(self):
        """Play or install the selected game based on its state."""
        items = self.library_list.selectedItems()
        if not items:
            return

        item = items[0]
        if not isinstance(item, GameListItem):
            return

        game = item.game
        game_id = game["id"]
        game_slug = game["slug"]

        try:
            # Get builds
            builds = self.api.get_builds(game_id)
            if not builds:
                QMessageBox.warning(self, "No Builds", "This game has no available builds.")
                return

            # Get latest build
            latest_build = max(builds, key=lambda b: b["id"])
            version = latest_build["version"]

            # Check if already installed
            if self.download_manager.is_installed(game_slug, version):
                # Game is installed - launch it
                self._launch_game(game, latest_build)
            else:
                # Game not installed - download it
                self._install_game(game, latest_build)

        except httpx.HTTPStatusError as e:
            QMessageBox.critical(self, "Error", f"API Error: {e.response.text}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _install_game(self, game: dict, build: dict):
        """Download and install a game (without launching)."""
        build_id = build["id"]
        expected_sha256 = build.get("sha256")
        
        try:
            # Get download URL
            download_url = self.api.get_download_url(build_id)

            # Start download with progress dialog (don't launch after)
            self._start_download(game, build, download_url, expected_sha256, launch_after=False)

        except httpx.HTTPStatusError as e:
            QMessageBox.critical(self, "Error", f"API Error: {e.response.text}")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def _start_download(self, game: dict, build: dict, url: str, expected_sha256: Optional[str], launch_after: bool = True):
        """Start downloading a game with progress dialog."""
        game_slug = game["slug"]
        version = build["version"]

        # Create progress dialog
        self.progress_dialog = QProgressDialog(
            f"Downloading {game['name']} v{version}...",
            "Cancel",
            0,
            100,
            self,
        )
        self.progress_dialog.setWindowTitle("Downloading")
        self.progress_dialog.setWindowModality(Qt.WindowModal)
        self.progress_dialog.setAutoClose(False)
        self.progress_dialog.setAutoReset(False)

        # Create download thread
        self.download_thread = DownloadThread(
            self.download_manager,
            url,
            game_slug,
            version,
            expected_sha256,
        )

        # Store game info for launch after download
        self._pending_game = game
        self._pending_build = build
        self._launch_after_download = launch_after

        # Connect signals
        self.download_thread.progress.connect(self._on_download_progress)
        self.download_thread.finished.connect(self._on_download_finished)
        self.download_thread.error.connect(self._on_download_error)
        self.progress_dialog.canceled.connect(self._on_download_canceled)

        # Start download
        self.download_thread.start()
        self.progress_dialog.show()

    def _on_download_progress(self, downloaded: int, total: int):
        """Update progress dialog."""
        if total > 0:
            percent = int(downloaded * 100 / total)
            self.progress_dialog.setValue(percent)
            mb_downloaded = downloaded / (1024 * 1024)
            mb_total = total / (1024 * 1024)
            self.progress_dialog.setLabelText(
                f"Downloading... {mb_downloaded:.1f} / {mb_total:.1f} MB"
            )

    def _on_download_finished(self, game_path: Path):
        """Handle successful download."""
        self.progress_dialog.close()
        self.statusBar().showMessage(f"Downloaded to {game_path}")
        
        # Refresh library to show installed status
        self._load_library()

        # Launch the game only if requested
        if getattr(self, "_launch_after_download", False):
            if hasattr(self, "_pending_game") and hasattr(self, "_pending_build"):
                self._launch_game(self._pending_game, self._pending_build)
        
        # Cleanup
        if hasattr(self, "_pending_game"):
            del self._pending_game
        if hasattr(self, "_pending_build"):
            del self._pending_build
        if hasattr(self, "_launch_after_download"):
            del self._launch_after_download

    def _on_download_error(self, error_msg: str):
        """Handle download error."""
        self.progress_dialog.close()
        QMessageBox.critical(self, "Download Failed", error_msg)

    def _on_download_canceled(self):
        """Handle download cancellation."""
        if hasattr(self, "download_thread") and self.download_thread.isRunning():
            self.download_thread.terminate()
            self.download_thread.wait()
        self.statusBar().showMessage("Download cancelled")

    def _launch_game(self, game: dict, build: dict):
        """Launch an installed game with DRM."""
        import zipfile
        import logging
        import platform
        
        logger = logging.getLogger("water.launcher")
        
        game_slug = game["slug"]
        version = build["version"]
        build_id = build["id"]

        try:
            # Get launch token
            launch_token = self.api.get_launch_token(build_id)
            access_token = self.api.access_token

            # Get game path
            game_path = self.download_manager.get_game_path(game_slug, version)
            zip_path = game_path / "game.zip"
            extracted_path = game_path / "extracted"
            
            # Extract if not already extracted
            if not extracted_path.exists():
                self.statusBar().showMessage(f"Extracting {game['name']}...")
                QApplication.processEvents()
                
                extracted_path.mkdir(parents=True, exist_ok=True)
                with zipfile.ZipFile(zip_path, "r") as zf:
                    zf.extractall(extracted_path)
                
                self.statusBar().showMessage(f"Extracted {game['name']}")
            
            logger.info(f"Looking for game executable in {extracted_path}")
            
            # DRM arguments to pass to the game
            drm_args = ["--token", launch_token, "--access", access_token, "--api", API_BASE]
            
            # Strategy 1: Look for native executable (Unity, Godot, compiled games)
            executable = self._find_native_executable(extracted_path, platform.system())
            if executable:
                logger.info(f"Found native executable: {executable}")
                cmd = [str(executable)] + drm_args
                cwd = executable.parent
            else:
                # Strategy 2: Look for Python package with __main__.py
                game_module = self._find_python_module(extracted_path)
                if game_module:
                    logger.info(f"Found Python module: {game_module}")
                    cmd = [sys.executable, "-m", game_module] + drm_args
                    cwd = extracted_path
                else:
                    QMessageBox.critical(
                        self,
                        "Launch Failed",
                        f"Could not find game executable in {extracted_path}\n\n"
                        "Expected one of:\n"
                        "- Native executable (.app, .exe, or Linux binary)\n"
                        "- Python package with __main__.py",
                    )
                    return
            
            logger.info(f"Launching game with command: {' '.join(cmd)}")
            logger.info(f"Working directory: {cwd}")
            
            self.statusBar().showMessage(f"Launching {game['name']}...")
            
            # Run the game in a separate process
            process = subprocess.Popen(cmd, cwd=str(cwd))
            
            self.statusBar().showMessage(f"Launched {game['name']} v{version} (PID: {process.pid})")
            logger.info(f"Game process started with PID: {process.pid}")

        except httpx.HTTPStatusError as e:
            QMessageBox.critical(self, "Launch Failed", f"Error: {e.response.text}")
        except Exception as e:
            logger.exception("Failed to launch game")
            QMessageBox.critical(self, "Launch Failed", str(e))

    def _find_native_executable(self, path: Path, system: str) -> Optional[Path]:
        """Find native game executable based on platform."""
        # macOS: Look for .app bundles
        if system == "Darwin":
            for item in path.rglob("*.app"):
                if item.is_dir():
                    # Return path to the actual binary inside .app
                    binary = item / "Contents" / "MacOS"
                    if binary.exists():
                        for exe in binary.iterdir():
                            if exe.is_file():
                                return exe
            # Also check for direct binaries (non-.app)
            for item in path.iterdir():
                if item.is_file() and not item.suffix and item.stat().st_mode & 0o111:
                    return item
        
        # Windows: Look for .exe files
        elif system == "Windows":
            for item in path.rglob("*.exe"):
                if item.is_file():
                    return item
        
        # Linux: Look for executable files without extension
        else:
            for item in path.iterdir():
                if item.is_file() and not item.suffix:
                    # Check if executable
                    if item.stat().st_mode & 0o111:
                        return item
            # Also check common patterns
            for pattern in ["*.x86_64", "*.x86", "*Linux*"]:
                for item in path.rglob(pattern):
                    if item.is_file():
                        return item
        
        return None

    def _find_python_module(self, path: Path) -> Optional[str]:
        """Find Python module with __main__.py."""
        for item in path.iterdir():
            if item.is_dir():
                # Check for Python package (with __main__.py)
                if (item / "__main__.py").exists():
                    return item.name
                # Check for subdirectory with __main__.py
                for subitem in item.iterdir():
                    if subitem.is_dir() and (subitem / "__main__.py").exists():
                        return subitem.name
        return None

    def _purchase_game(self):
        items = self.store_list.selectedItems()
        if not items:
            return

        item = items[0]
        if not isinstance(item, GameListItem):
            return

        game = item.game
        if game.get("owned"):
            return

        # Confirm purchase
        reply = QMessageBox.question(
            self,
            "Confirm Purchase",
            f"Purchase '{game['name']}' for ${game['price']}?",
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply != QMessageBox.Yes:
            return

        try:
            self.api.purchase(game["id"])
            QMessageBox.information(
                self,
                "Purchase Complete",
                f"You now own '{game['name']}'!",
            )
            # Refresh both lists
            self._load_library()
            self._load_store()

        except httpx.HTTPStatusError as e:
            try:
                detail = e.response.json().get("detail", str(e))
            except Exception:
                detail = e.response.text
            QMessageBox.critical(self, "Purchase Failed", f"Error: {detail}")
        except Exception as e:
            QMessageBox.critical(self, "Purchase Failed", str(e))

    def _uninstall_game(self):
        """Uninstall the selected game from local storage."""
        items = self.library_list.selectedItems()
        if not items:
            return

        item = items[0]
        if not isinstance(item, GameListItem):
            return

        game = item.game
        game_slug = game["slug"]

        # Confirm uninstall
        reply = QMessageBox.question(
            self,
            "Confirm Uninstall",
            f"Uninstall '{game['name']}'?\n\n"
            f"This will delete all downloaded files for this game.",
            QMessageBox.Yes | QMessageBox.No,
        )

        if reply != QMessageBox.Yes:
            return

        try:
            # Delete all versions of this game
            if self.download_manager.delete_game(game_slug):
                QMessageBox.information(
                    self,
                    "Uninstalled",
                    f"'{game['name']}' has been uninstalled.",
                )
                self._load_library()  # Refresh to update installed status
            else:
                QMessageBox.warning(
                    self,
                    "Not Installed",
                    f"'{game['name']}' is not installed.",
                )
        except Exception as e:
            QMessageBox.critical(self, "Uninstall Failed", str(e))


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Water Launcher")
    app.setStyle("Fusion")

    api = ApiClient()
    window = MainWindow(api)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
