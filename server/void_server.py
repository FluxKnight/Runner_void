# server/void_server.py
# VOID RUNNER persistent global account/rank server.
#
# Storage modes:
#   1. Supabase database when SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY/SUPABASE_SECRET_KEY are set.
#   2. Local JSON fallback when Supabase is not configured.
#
# Local test:
#   python server/void_server.py
#
# Render start command:
#   python server/void_server.py

import hashlib
import json
import os
import secrets
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError


HOST = "0.0.0.0"
PORT = int(os.environ.get("PORT", "5050"))

DATA_DIR = Path(__file__).resolve().parent / "data"
USERS_FILE = DATA_DIR / "server_users.json"

SUPABASE_URL = os.environ.get("SUPABASE_URL", "").rstrip("/")
SUPABASE_KEY = (
    os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    or os.environ.get("SUPABASE_SECRET_KEY")
    or os.environ.get("SUPABASE_KEY")
    or ""
).strip()
SUPABASE_TABLE = os.environ.get("SUPABASE_TABLE", "void_runner_users").strip() or "void_runner_users"


def database_enabled():
    return bool(SUPABASE_URL and SUPABASE_KEY)


def default_profile(username, password=""):
    return {
        "username": username,
        # Keep this key for old client compatibility. The server never stores raw passwords in Supabase.
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


def safe_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def normalize_profile(profile):
    if not isinstance(profile, dict):
        profile = {}

    username = str(profile.get("username") or "Player")
    password = str(profile.get("password") or "")
    merged = default_profile(username, password)
    merged.update(profile)

    merged["username"] = username
    merged["owned_skins"] = sorted(set(list(merged.get("owned_skins") or []) + ["WHITE"]))
    merged["owned_guns"] = sorted(set(list(merged.get("owned_guns") or []) + ["PISTOL"]))
    merged.setdefault("display_name", username)
    merged["best_level"] = max(1, safe_int(merged.get("best_level"), 1))
    merged["best_gems"] = max(0, safe_int(merged.get("best_gems"), 0))
    merged["best_score"] = max(0, safe_int(merged.get("best_score"), 0))
    merged["wallet_gems"] = max(0, safe_int(merged.get("wallet_gems"), 0))
    merged["total_gems_collected"] = max(0, safe_int(merged.get("total_gems_collected"), 0))
    return merged


def sanitize_profile(profile):
    profile = normalize_profile(profile)
    # Never save password/raw password data inside the JSON profile in Supabase.
    profile.pop("password", None)
    profile.pop("password_hash", None)
    profile.pop("salt", None)
    return profile


def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)
    raw = f"{salt}:{password}".encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    return salt, digest


def verify_password(password, password_hash):
    try:
        salt, digest = str(password_hash).split(":", 1)
    except ValueError:
        return False
    _, attempt = hash_password(password, salt=salt)
    return secrets.compare_digest(attempt, digest)


def supabase_request(method, path, payload=None):
    if not database_enabled():
        raise RuntimeError("Supabase is not configured")

    url = f"{SUPABASE_URL}/rest/v1/{path}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
    }

    data = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        if method.upper() in ("POST", "PATCH"):
            headers["Prefer"] = "return=representation"

    req = Request(url, data=data, headers=headers, method=method.upper())
    try:
        with urlopen(req, timeout=7) as res:
            body = res.read().decode("utf-8")
            if not body:
                return None
            return json.loads(body)
    except HTTPError as err:
        body = err.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Supabase HTTP {err.code}: {body}") from err
    except URLError as err:
        raise RuntimeError(f"Supabase connection error: {err}") from err


def row_to_profile(row):
    profile = row.get("profile") or {}
    if not isinstance(profile, dict):
        profile = {}
    profile["username"] = row.get("username") or profile.get("username") or "Player"
    return normalize_profile(profile)


def supabase_get_user_row(username):
    username_q = quote(username, safe="")
    rows = supabase_request("GET", f"{SUPABASE_TABLE}?username=eq.{username_q}&select=*")
    if isinstance(rows, list) and rows:
        return rows[0]
    return None


def supabase_load_users():
    rows = supabase_request("GET", f"{SUPABASE_TABLE}?select=*&order=updated_at.desc")
    users = {}
    if isinstance(rows, list):
        for row in rows:
            username = row.get("username")
            if username:
                users[username] = row_to_profile(row)
    return users


def supabase_create_user(username, password):
    if supabase_get_user_row(username):
        return False, "Username already exists."

    salt, digest = hash_password(password)
    profile = sanitize_profile(default_profile(username))
    row = {
        "username": username,
        "password_hash": f"{salt}:{digest}",
        "profile": profile,
    }
    supabase_request("POST", SUPABASE_TABLE, row)
    return True, "Account created."


def merge_profiles(old_profile, new_profile):
    old = normalize_profile(old_profile)
    new = normalize_profile(new_profile)

    old.update(new)
    old["best_score"] = max(safe_int(old_profile.get("best_score", 0)), safe_int(new_profile.get("best_score", 0)))
    old["best_level"] = max(safe_int(old_profile.get("best_level", 1)), safe_int(new_profile.get("best_level", 1)))
    old["best_gems"] = max(safe_int(old_profile.get("best_gems", 0)), safe_int(new_profile.get("best_gems", 0)))
    old["wallet_gems"] = max(safe_int(old_profile.get("wallet_gems", 0)), safe_int(new_profile.get("wallet_gems", 0)))
    old["total_gems_collected"] = max(
        safe_int(old_profile.get("total_gems_collected", 0)),
        safe_int(new_profile.get("total_gems_collected", 0)),
    )
    old["owned_skins"] = sorted(set(list(old_profile.get("owned_skins") or []) + list(new_profile.get("owned_skins") or []) + ["WHITE"]))
    old["owned_guns"] = sorted(set(list(old_profile.get("owned_guns") or []) + list(new_profile.get("owned_guns") or []) + ["PISTOL"]))
    return sanitize_profile(old)


def supabase_update_profile(username, profile):
    row = supabase_get_user_row(username)
    if row:
        current = row_to_profile(row)
    else:
        # This path is for migrated/offline profiles that sync before explicit server account creation.
        # Password will be blank, so the account should later be recreated by the player if needed.
        current = default_profile(username)
        salt, digest = hash_password(str(profile.get("password") or ""))
        supabase_request("POST", SUPABASE_TABLE, {
            "username": username,
            "password_hash": f"{salt}:{digest}",
            "profile": sanitize_profile(current),
        })

    merged = merge_profiles(current, profile)
    username_q = quote(username, safe="")
    rows = supabase_request("PATCH", f"{SUPABASE_TABLE}?username=eq.{username_q}", {"profile": merged})
    if isinstance(rows, list) and rows:
        return row_to_profile(rows[0])
    return merged


def local_load_users():
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


def local_save_users(users):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    USERS_FILE.write_text(json.dumps(users, indent=2), encoding="utf-8")


def load_users():
    if database_enabled():
        return supabase_load_users()
    return local_load_users()


def save_users(users):
    # Only local fallback uses bulk save. Supabase writes through specific functions.
    if not database_enabled():
        local_save_users(users)


class Handler(BaseHTTPRequestHandler):
    def send_json(self, payload, status=200):
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self):
        self.send_json({"ok": True})

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

    def safe_load_users_response(self):
        try:
            users = load_users()
            return {"ok": True, "users": users, "storage": "supabase" if database_enabled() else "local_file"}
        except Exception as exc:
            return {"ok": False, "message": str(exc), "users": {}, "storage": "error"}

    def do_GET(self):
        path = urlparse(self.path).path

        if path in ("/", "/health"):
            status = self.safe_load_users_response()
            self.send_json({
                "ok": status.get("ok", False),
                "message": "VOID RUNNER persistent global server online" if status.get("ok") else "VOID RUNNER server online, database error",
                "storage": status.get("storage"),
                "users": len(status.get("users", {})),
                "database": "supabase" if database_enabled() else "local_file_fallback",
                "database_configured": database_enabled(),
                "error": status.get("message") if not status.get("ok") else None,
            })
            return

        if path in ("/users", "/ranks"):
            status = self.safe_load_users_response()
            self.send_json(status, status=200 if status.get("ok") else 500)
            return

        if path == "/debug_users":
            status = self.safe_load_users_response()
            users = status.get("users", {})
            self.send_json({
                "ok": status.get("ok", False),
                "storage": status.get("storage"),
                "count": len(users),
                "usernames": list(users.keys()),
                "users": users,
                "message": status.get("message"),
            }, status=200 if status.get("ok") else 500)
            return

        self.send_json({"ok": False, "message": "Not found"}, status=404)

    def do_POST(self):
        path = urlparse(self.path).path
        payload = self.read_json()

        try:
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

                if database_enabled():
                    ok, message = supabase_create_user(username, password)
                    if not ok:
                        self.send_json({"ok": False, "message": message})
                        return
                    users = load_users()
                    self.send_json({"ok": True, "message": message, "users": users, "storage": "supabase"})
                    return

                users = local_load_users()
                if username in users:
                    self.send_json({"ok": False, "message": "Username already exists."})
                    return
                users[username] = default_profile(username, password)
                local_save_users(users)
                self.send_json({"ok": True, "message": "Account created.", "users": users, "storage": "local_file"})
                return

            if path == "/login":
                username = str(payload.get("username", "")).strip()
                password = str(payload.get("password", "")).strip()

                if database_enabled():
                    row = supabase_get_user_row(username)
                    if not row:
                        self.send_json({"ok": False, "message": "Account not found."})
                        return
                    if not verify_password(password, row.get("password_hash", "")):
                        self.send_json({"ok": False, "message": "Wrong password."})
                        return
                    profile = row_to_profile(row)
                    users = load_users()
                    self.send_json({"ok": True, "message": "Logged in.", "profile": profile, "users": users, "storage": "supabase"})
                    return

                users = local_load_users()
                user = users.get(username)
                if not user:
                    self.send_json({"ok": False, "message": "Account not found."})
                    return
                if user.get("password") != password:
                    self.send_json({"ok": False, "message": "Wrong password."})
                    return
                self.send_json({"ok": True, "message": "Logged in.", "profile": user, "users": users, "storage": "local_file"})
                return

            if path == "/sync_profile":
                username = str(payload.get("username", "")).strip()
                profile = payload.get("profile", {})
                if not username or not isinstance(profile, dict):
                    self.send_json({"ok": False, "message": "Bad profile payload."})
                    return

                if database_enabled():
                    updated = supabase_update_profile(username, profile)
                    users = load_users()
                    self.send_json({"ok": True, "message": "Profile synced.", "profile": updated, "users": users, "storage": "supabase"})
                    return

                users = local_load_users()
                old = users.get(username, default_profile(username, profile.get("password", "")))
                users[username] = merge_profiles(old, profile)
                # local fallback keeps old raw password behavior for compatibility.
                if old.get("password"):
                    users[username]["password"] = old.get("password")
                local_save_users(users)
                self.send_json({"ok": True, "message": "Profile synced.", "profile": users[username], "users": users, "storage": "local_file"})
                return

            self.send_json({"ok": False, "message": "Not found"}, status=404)
        except Exception as exc:
            self.send_json({"ok": False, "message": str(exc), "storage": "supabase" if database_enabled() else "local_file"}, status=500)

    def log_message(self, fmt, *args):
        print("[VOID PERSISTENT SERVER]", fmt % args)


def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    storage = "Supabase" if database_enabled() else "local JSON fallback"
    print(f"VOID RUNNER persistent global server running on 0.0.0.0:{PORT}")
    print(f"Storage: {storage}")
    print(f"Local test URL: http://127.0.0.1:{PORT}/health")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


if __name__ == "__main__":
    main()
