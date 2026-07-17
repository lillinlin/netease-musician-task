"""Web 管理端密码与会话认证。"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from dataclasses import dataclass
from typing import Optional

from app import repository as repo

DEFAULT_ADMIN_PASSWORD = "123456"
PASSWORD_SETTING_KEY = "admin_password_hash"
SESSION_COOKIE = "netease_admin_session"
SESSION_TTL_SECONDS = 7 * 24 * 60 * 60
PBKDF2_ITERATIONS = 260_000


@dataclass
class Session:
    expires_at: float
    must_change_password: bool


_sessions: dict[str, Session] = {}


def _hash_password(password: str, *, salt: Optional[bytes] = None) -> str:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return f"pbkdf2_sha256${PBKDF2_ITERATIONS}${salt.hex()}${digest.hex()}"


def _verify_hash(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations, salt_hex, digest_hex = encoded.split("$", 3)
        if algorithm != "pbkdf2_sha256":
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt_hex), int(iterations)
        )
        return hmac.compare_digest(actual, bytes.fromhex(digest_hex))
    except (TypeError, ValueError):
        return False


def ensure_admin_password() -> None:
    if not repo.get_setting(PASSWORD_SETTING_KEY, ""):
        repo.set_setting(PASSWORD_SETTING_KEY, _hash_password(DEFAULT_ADMIN_PASSWORD))


def verify_password(password: str) -> bool:
    ensure_admin_password()
    return _verify_hash(password, repo.get_setting(PASSWORD_SETTING_KEY, "") or "")


def is_default_password(password: str) -> bool:
    return password == DEFAULT_ADMIN_PASSWORD and verify_password(password)


def create_session(*, must_change_password: bool) -> str:
    _purge_expired()
    token = secrets.token_urlsafe(32)
    _sessions[token] = Session(time.time() + SESSION_TTL_SECONDS, must_change_password)
    return token


def get_session(token: Optional[str]) -> Optional[Session]:
    if not token:
        return None
    session = _sessions.get(token)
    if session is None or session.expires_at <= time.time():
        _sessions.pop(token, None)
        return None
    return session


def change_password(current_password: str, new_password: str) -> None:
    if not verify_password(current_password):
        raise ValueError("当前管理密码错误")
    if len(new_password) < 6:
        raise ValueError("新密码至少需要 6 位")
    if new_password == DEFAULT_ADMIN_PASSWORD:
        raise ValueError("新密码不能继续使用默认密码 123456")
    repo.set_setting(PASSWORD_SETTING_KEY, _hash_password(new_password))
    _sessions.clear()


def delete_session(token: Optional[str]) -> None:
    if token:
        _sessions.pop(token, None)


def _purge_expired() -> None:
    now = time.time()
    for token, session in list(_sessions.items()):
        if session.expires_at <= now:
            _sessions.pop(token, None)
