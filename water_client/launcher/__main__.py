"""
Water Launcher - Desktop client for Water game store.

A PySide6-based game launcher that handles:
- User authentication (login/register)
- Game library browsing
- Store browsing and purchases
- Game downloads and launching
"""

import sys
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
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
import httpx

from .config import API_BASE


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

    def __init__(self, game: dict):
        self.game = game
        owned = game.get("owned", True)  # Library items are always owned
        price = game.get("price", "0.00")

        if owned:
            text = f"✓ {game['name']}"
        else:
            text = f"{game['name']} - ${price}"

        super().__init__(text)

        if owned:
            self.setForeground(Qt.darkGreen)


class MainWindow(QMainWindow):
    """Main launcher window."""

    def __init__(self, api: ApiClient):
        super().__init__()
        self.api = api
        self.setWindowTitle("Water Launcher")
        self.setMinimumSize(600, 450)

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
        self.library_list = QListWidget()
        self.library_list.itemDoubleClicked.connect(self._play_game)
        library_layout.addWidget(QLabel("Your Games:"))
        library_layout.addWidget(self.library_list)

        btn_layout = QHBoxLayout()
        self.play_btn = QPushButton("▶ Play")
        self.play_btn.clicked.connect(self._play_game)
        self.play_btn.setEnabled(False)
        btn_layout.addWidget(self.play_btn)
        self.refresh_btn = QPushButton("🔄 Refresh")
        self.refresh_btn.clicked.connect(self._load_library)
        btn_layout.addWidget(self.refresh_btn)
        library_layout.addLayout(btn_layout)

        self.tabs.addTab(library_widget, "📚 Library")

        # Store tab
        store_widget = QWidget()
        store_layout = QVBoxLayout(store_widget)
        self.store_list = QListWidget()
        self.store_list.itemSelectionChanged.connect(self._store_selection_changed)
        store_layout.addWidget(QLabel("Available Games:"))
        store_layout.addWidget(self.store_list)

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
                self.library_list.addItem(GameListItem(game))
            self.statusBar().showMessage(f"Loaded {len(games)} games")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load library: {e}")

    def _load_store(self):
        try:
            games = self.api.get_store()
            self.store_list.clear()
            for game in games:
                self.store_list.addItem(GameListItem(game))
            self.statusBar().showMessage(f"Loaded {len(games)} games from store")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load store: {e}")

    def _library_selection_changed(self):
        self.play_btn.setEnabled(len(self.library_list.selectedItems()) == 1)

    def _store_selection_changed(self):
        items = self.store_list.selectedItems()
        if items:
            item = items[0]
            if isinstance(item, GameListItem):
                # Enable buy only if not owned
                self.buy_btn.setEnabled(not item.game.get("owned", False))
            else:
                self.buy_btn.setEnabled(False)
        else:
            self.buy_btn.setEnabled(False)

    def _play_game(self):
        items = self.library_list.selectedItems()
        if not items:
            return

        item = items[0]
        if not isinstance(item, GameListItem):
            return

        game = item.game
        game_id = game["id"]

        try:
            # Get builds
            builds = self.api.get_builds(game_id)
            if not builds:
                QMessageBox.warning(self, "No Builds", "This game has no available builds.")
                return

            # Get latest build
            latest_build = max(builds, key=lambda b: b["id"])
            build_id = latest_build["id"]

            # Get launch token
            launch_token = self.api.get_launch_token(build_id)

            # Show success - in real app would launch the game
            QMessageBox.information(
                self,
                "Launch Ready",
                f"Game: {game['name']}\n"
                f"Build: v{latest_build['version']}\n"
                f"Launch token obtained!\n\n"
                f"In a full implementation, the game would now start with DRM validation.",
            )

            self.statusBar().showMessage(f"Launched {game['name']} v{latest_build['version']}")

        except httpx.HTTPStatusError as e:
            QMessageBox.critical(self, "Launch Failed", f"Error: {e.response.text}")
        except Exception as e:
            QMessageBox.critical(self, "Launch Failed", str(e))

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
