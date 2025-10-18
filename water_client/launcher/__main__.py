
import sys
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QListWidget, QMessageBox
import httpx
from .config import API_BASE

class Launcher(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("water Launcher")
        self.access = None
        self.user_label = QLabel("Not logged in")
        self.btn_login = QPushButton("Login (demo)")
        self.btn_games = QPushButton("Load My Games")
        self.btn_games.setEnabled(False)
        self.list_games = QListWidget()
        self.btn_play = QPushButton("Play Selected")
        self.btn_play.setEnabled(False)

        lay = QVBoxLayout(self)
        lay.addWidget(self.user_label)
        lay.addWidget(self.btn_login)
        lay.addWidget(self.btn_games)
        lay.addWidget(self.list_games)
        lay.addWidget(self.btn_play)

        self.btn_login.clicked.connect(self.login)
        self.btn_games.clicked.connect(self.load_games)
        self.list_games.itemSelectionChanged.connect(self._sel_changed)
        self.btn_play.clicked.connect(self.play_selected)

    def _sel_changed(self):
        self.btn_play.setEnabled(len(self.list_games.selectedItems()) == 1)

    def login(self):
        try:
            r = httpx.post(f"{API_BASE}/auth/login", json={"email":"test@example.com","password":"test"}, timeout=10.0)
            r.raise_for_status()
            self.access = r.json()["access_token"]
            self.user_label.setText("Logged in as test@example.com")
            self.btn_games.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "Login failed", str(e))

    def load_games(self):
        try:
            r = httpx.get(f"{API_BASE}/games/", headers={"Authorization": f"Bearer {self.access}"} , timeout=10.0)
            r.raise_for_status()
            self.list_games.clear()
            for g in r.json():
                self.list_games.addItem(f"{g['id']} – {g['name']} ({g['slug']})")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def play_selected(self):
        item = self.list_games.selectedItems()[0]
        game_id = int(item.text().split(" – ")[0])
        try:
            # Fetch builds for the selected game
            builds_resp = httpx.get(f"{API_BASE}/games/{game_id}/builds", headers={"Authorization": f"Bearer {self.access}"}, timeout=10.0)
            builds_resp.raise_for_status()
            builds = builds_resp.json()
            if not builds:
                QMessageBox.critical(self, "Launch failed", "No builds available for this game.")
                return
            # Select the latest build (by highest id)
            latest_build = max(builds, key=lambda b: b.get("id", 0))
            build_id = latest_build["id"]
            r = httpx.post(f"{API_BASE}/launch/{build_id}", headers={"Authorization": f"Bearer {self.access}"}, timeout=10.0)
            r.raise_for_status()
            token = r.json()["token"]
            # Demo: immediately attest + one heartbeat
            a = httpx.post(f"{API_BASE}/sessions/attest", json={"token": token}, headers={"Authorization": f"Bearer {self.access}"}, timeout=10.0)
            a.raise_for_status()
            session_id = a.json()["session_id"]
            h = httpx.post(f"{API_BASE}/sessions/{session_id}/heartbeat", headers={"Authorization": f"Bearer {self.access}"}, timeout=10.0)
            h.raise_for_status()
            QMessageBox.information(self, "Launched", f"Session {session_id} created and heartbeat sent.")
        except Exception as e:
            QMessageBox.critical(self, "Launch failed", str(e))

def main():
    app = QApplication(sys.argv)
    w = Launcher()
    w.resize(480, 360)
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
