# server/void_server.py
# VOID RUNNER global-ready account/rank server.
#
# Local run:
#   python server/void_server.py
#
# Global deploy:
#   Host this server on Render/Railway/Fly/etc.
#   The host provides a public URL.
#   Then put that URL in the game client's data/server_config.json:
#   {"server_url": "https://YOUR-SERVER-URL"}
#
# Notes:
# - This is a simple learning/game prototype server.
# - It supports global accounts/ranks when hosted publicly.
# - For a real production game, use password hashing + proper database.

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse


HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "5050"))

DATA_DIR = Path(__file__).resolve().parent / "data"
USERS_FILE = DATA_DIR / "server_users.json"


def default_profile(username, password):
    return {
        "username": username,
        "password": password,
        "display_name": username,
        "wallet_gems": 0,
        "best_score": 0,
        "best_level": 1,
        "best_gems": 0,
        "total_gems_collected": 0,
        "owned_skins": ["WHITE"],
        "active_skin": "WHITE",
        "owned_guns": ["PISTOL"],
        "active_gun": "PISTOL",
    }


def normalize_profile(profile):
    username = profile.get("username", "Player")
    password = profile.get("password", "")
    default = default_profile(username, password)
    default.update(profile)

    default["owned_skins"] = sorted(set(default.get("owned_skins", ["WHITE"]) + ["WHITE"]))
    default["owned_guns"] = sorted(set(default.get("owned_guns", ["PISTOL"]) + ["PISTOL"]))

    default.setdefault("display_name", username)
    default.setdefault("best_level", 1)
    default.setdefault("best_gems", 0)
    default.setdefault("best_score", 0)
    default.setdefault("total_gems_collected", 0)
    return default


def load_users():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not USERS_FILE.exists():
        USERS_FILE.write_text("{}", encoding="utf-8")
        return {}

    try:
        data = json.loads(USERS_FILE.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            return {name: normalize_profile(profile) for name, profile in data.items()}
    except Exception:
        pass

    return {}


def save_users(users):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    USERS_FILE.write_text(json.dumps(users, indent=2), encoding="utf-8")


def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


class Handler(BaseHTTPRequestHandler):
    def send_json(self, payload, status=200):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def read_json(self):
        length = int(self.headers.get("Content-Length", "0") or "0")
        if length <= 0:
            return {}
        body = self.rfile.read(length).decode("utf-8")
        try:
            data = json.loads(body)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def do_GET(self):
        path = urlparse(self.path).path

        if path in ("/", "/health"):
            self.send_json({
                "ok": True,
                "message": "VOID RUNNER global server online",
                "users": len(load_users()),
            })
            return

        if path in ("/users", "/ranks"):
            users = load_users()
            self.send_json({"ok": True, "users": users})
            return

        if path == "/debug_users":
            users = load_users()
            self.send_json({
                "ok": True,
                "count": len(users),
                "usernames": list(users.keys()),
                "users": users,
            })
            return

        self.send_json({"ok": False, "message": "Not found"}, status=404)

    def do_POST(self):
        path = urlparse(self.path).path
        payload = self.read_json()
        users = load_users()

        if path == "/create_account":
            username = str(payload.get("username", "")).strip()
            password = str(payload.get("password", "")).strip()
            confirm = str(payload.get("confirm_password", "")).strip()

            if len(username) < 3:
                self.send_json({"ok": False, "message": "Username must be at least 3 characters."})
                return

            if len(password) < 3:
                self.send_json({"ok": False, "message": "Password must be at least 3 characters."})
                return

            if password != confirm:
                self.send_json({"ok": False, "message": "Passwords do not match."})
                return

            if username in users:
                self.send_json({"ok": False, "message": "Username already exists."})
                return

            users[username] = default_profile(username, password)
            save_users(users)
            self.send_json({"ok": True, "message": "Account created.", "users": users})
            return

        if path == "/login":
            username = str(payload.get("username", "")).strip()
            password = str(payload.get("password", "")).strip()

            user = users.get(username)

            if not user:
                self.send_json({"ok": False, "message": "Account not found."})
                return

            if user.get("password") != password:
                self.send_json({"ok": False, "message": "Wrong password."})
                return

            self.send_json({"ok": True, "message": "Logged in.", "profile": user, "users": users})
            return

        if path == "/sync_profile":
            username = str(payload.get("username", "")).strip()
            profile = payload.get("profile", {})

            if not username or not isinstance(profile, dict):
                self.send_json({"ok": False, "message": "Bad profile payload."})
                return

            old = users.get(username, default_profile(username, profile.get("password", "")))
            old.update(profile)

            # Keep best values from either side.
            old["best_score"] = max(safe_int(old.get("best_score", 0)), safe_int(profile.get("best_score", 0)))
            old["best_level"] = max(safe_int(old.get("best_level", 1)), safe_int(profile.get("best_level", 1)))
            old["best_gems"] = max(safe_int(old.get("best_gems", 0)), safe_int(profile.get("best_gems", 0)))
            old["wallet_gems"] = max(safe_int(old.get("wallet_gems", 0)), safe_int(profile.get("wallet_gems", 0)))
            old["total_gems_collected"] = max(
                safe_int(old.get("total_gems_collected", 0)),
                safe_int(profile.get("total_gems_collected", 0)),
            )

            users[username] = normalize_profile(old)
            save_users(users)
            self.send_json({"ok": True, "message": "Profile synced.", "profile": users[username], "users": users})
            return

        self.send_json({"ok": False, "message": "Not found"}, status=404)

    def log_message(self, fmt, *args):
        print("[VOID GLOBAL SERVER]", fmt % args)


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"VOID RUNNER global server running on 0.0.0.0:{PORT}")
    print(f"Local test URL: http://127.0.0.1:{PORT}")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


if __name__ == "__main__":
    main()
