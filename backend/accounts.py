"""Lightweight, file-backed user accounts for the Game Review app.

This is a *local* tool, so we keep things deliberately simple — no database, no
external auth library. Everything lives under ``backend/data/accounts/``:

    accounts/
        users.json                 # {username: {salt, hash, created_at}}
        games/<username>/<id>.json # one saved review per file

Passwords are hashed with PBKDF2-HMAC-SHA256 (stdlib ``hashlib``) and a random
per-user salt — never stored in plaintext. Sessions are opaque bearer tokens
(``secrets.token_urlsafe``) kept in memory; restarting the server simply asks
users to sign in again, which is fine for a single-machine tool.

The store is process-wide and guarded by a lock so the FastAPI threads can share
one instance safely.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import threading
import time
from typing import Optional

_DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "accounts")
_USERS_FILE = os.path.join(_DATA_DIR, "users.json")
_GAMES_DIR = os.path.join(_DATA_DIR, "games")

_PBKDF2_ROUNDS = 200_000
_USERNAME_RE = re.compile(r"^[A-Za-z0-9_-]{3,32}$")
_SLUG_RE = re.compile(r"[^a-z0-9]+")


class AccountError(Exception):
    """Raised for predictable account problems (bad input, conflicts, auth)."""

    def __init__(self, message: str, status: int = 400) -> None:
        super().__init__(message)
        self.status = status


def _hash_password(password: str, salt: bytes) -> str:
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ROUNDS)
    return dk.hex()


class AccountStore:
    """Thread-safe, JSON-backed users + their saved games."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._tokens: dict[str, str] = {}          # token -> username
        self._users: dict[str, dict] = self._load_users()

    # ---- persistence ------------------------------------------------------ #
    def _load_users(self) -> dict[str, dict]:
        if not os.path.isfile(_USERS_FILE):
            return {}
        with open(_USERS_FILE, encoding="utf-8") as fh:
            return json.load(fh)

    def _save_users(self) -> None:
        os.makedirs(_DATA_DIR, exist_ok=True)
        tmp = _USERS_FILE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(self._users, fh, indent=2)
        os.replace(tmp, _USERS_FILE)

    def _user_games_dir(self, username: str) -> str:
        return os.path.join(_GAMES_DIR, username)

    # ---- registration / auth --------------------------------------------- #
    def register(self, username: str, password: str) -> str:
        username = (username or "").strip()
        if not _USERNAME_RE.match(username):
            raise AccountError(
                "Username must be 3–32 chars: letters, digits, '-' or '_'.", 400
            )
        if len(password or "") < 4:
            raise AccountError("Password must be at least 4 characters.", 400)
        with self._lock:
            if username.lower() in {u.lower() for u in self._users}:
                raise AccountError("That username is already taken.", 409)
            salt = secrets.token_bytes(16)
            self._users[username] = {
                "salt": salt.hex(),
                "hash": _hash_password(password, salt),
                "created_at": time.time(),
            }
            self._save_users()
            return self._issue_token(username)

    def login(self, username: str, password: str) -> str:
        with self._lock:
            # Case-insensitive lookup, but keep the stored canonical spelling.
            canonical = next(
                (u for u in self._users if u.lower() == (username or "").strip().lower()),
                None,
            )
            rec = self._users.get(canonical) if canonical else None
            if not rec or _hash_password(password or "", bytes.fromhex(rec["salt"])) != rec["hash"]:
                raise AccountError("Invalid username or password.", 401)
            return self._issue_token(canonical)

    def _issue_token(self, username: str) -> str:
        token = secrets.token_urlsafe(32)
        self._tokens[token] = username
        return token

    def logout(self, token: str) -> None:
        with self._lock:
            self._tokens.pop(token, None)

    def user_for_token(self, token: Optional[str]) -> str:
        with self._lock:
            user = self._tokens.get(token or "")
        if not user:
            raise AccountError("Not signed in.", 401)
        return user

    # ---- saved games ------------------------------------------------------ #
    def _game_path(self, username: str, game_id: str) -> str:
        if not re.fullmatch(r"[a-z0-9-]{1,80}", game_id):
            raise AccountError("Invalid game id.", 400)
        return os.path.join(self._user_games_dir(username), f"{game_id}.json")

    def save_game(self, username: str, review: dict, *, name: str = "") -> dict:
        """Persist a review dict for a user; returns the stored catalogue entry."""
        white = review.get("white") or "White"
        black = review.get("black") or "Black"
        title = (name or "").strip() or f"{white} vs {black}"
        slug = _SLUG_RE.sub("-", title.lower()).strip("-")[:48] or "game"
        game_id = f"{slug}-{secrets.token_hex(3)}"

        summary = review.get("summary") or {}
        entry = {
            "id": game_id,
            "name": title,
            "white": white,
            "black": black,
            "result": review.get("result") or "*",
            "opening": review.get("opening"),
            "move_count": len(review.get("moves") or []),
            "accuracy_white": _accuracy(summary.get("white", {}).get("avg_centipawn_loss", 0)),
            "accuracy_black": _accuracy(summary.get("black", {}).get("avg_centipawn_loss", 0)),
            "saved_at": time.time(),
        }
        with self._lock:
            os.makedirs(self._user_games_dir(username), exist_ok=True)
            payload = {"meta": entry, "review": review}
            path = self._game_path(username, game_id)
            with open(path, "w", encoding="utf-8") as fh:
                json.dump(payload, fh)
        return entry

    def list_games(self, username: str) -> list[dict]:
        d = self._user_games_dir(username)
        if not os.path.isdir(d):
            return []
        games = []
        for fname in os.listdir(d):
            if not fname.endswith(".json"):
                continue
            try:
                with open(os.path.join(d, fname), encoding="utf-8") as fh:
                    games.append(json.load(fh)["meta"])
            except (OSError, ValueError, KeyError):
                continue
        games.sort(key=lambda g: g.get("saved_at", 0), reverse=True)
        return games

    def get_game(self, username: str, game_id: str) -> dict:
        path = self._game_path(username, game_id)
        if not os.path.isfile(path):
            raise AccountError("Saved game not found.", 404)
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)["review"]

    def delete_game(self, username: str, game_id: str) -> None:
        path = self._game_path(username, game_id)
        if not os.path.isfile(path):
            raise AccountError("Saved game not found.", 404)
        os.remove(path)


def _accuracy(avg_cpl: float) -> float:
    """lichess-style accuracy% from average centipawn loss (cpl in centipawns)."""
    import math

    acc = 103.1668 * math.exp(-0.04354 * (avg_cpl / 100)) - 3.1669
    return round(max(0.0, min(100.0, acc)), 1)


# A single process-wide store shared by the API.
STORE = AccountStore()


# --------------------------------------------------------------------------- #
# CLI: seed a few test accounts for trying the feature out.
#   python -m backend.accounts seed
# --------------------------------------------------------------------------- #
_TEST_ACCOUNTS = [
    ("alice", "alice123"),
    ("bob", "bob123"),
    ("carol", "carol123"),
]


def seed_test_accounts() -> None:
    created, existed = [], []
    for username, password in _TEST_ACCOUNTS:
        try:
            STORE.register(username, password)
            created.append(username)
        except AccountError as exc:
            if exc.status == 409:
                existed.append(username)
            else:
                raise
    print("Test accounts:")
    for username, password in _TEST_ACCOUNTS:
        tag = "created" if username in created else "already existed"
        print(f"  • {username} / {password}   ({tag})")
    print(f"\nUsers file: {_USERS_FILE}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "seed":
        seed_test_accounts()
    else:
        print("Usage: python -m backend.accounts seed")
