"""Web 管理端登录、改密和退出。"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from app.web_auth import (
    SESSION_COOKIE,
    change_password,
    create_session,
    delete_session,
    get_session,
    is_default_password,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])
_failed_attempts: dict[str, deque[float]] = defaultdict(deque)
_MAX_ATTEMPTS = 5
_ATTEMPT_WINDOW_SECONDS = 300


class LoginBody(BaseModel):
    password: str


class ChangePasswordBody(BaseModel):
    current_password: str
    new_password: str


def _set_cookie(response: Response, token: str, *, secure: bool) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=7 * 24 * 60 * 60,
        httponly=True,
        secure=secure,
        samesite="strict",
        path="/",
    )


@router.post("/login")
def login(body: LoginBody, request: Request, response: Response) -> dict:
    client = request.client.host if request.client else "unknown"
    now = time.time()
    attempts = _failed_attempts[client]
    while attempts and attempts[0] <= now - _ATTEMPT_WINDOW_SECONDS:
        attempts.popleft()
    if len(attempts) >= _MAX_ATTEMPTS:
        raise HTTPException(429, "登录失败次数过多，请 5 分钟后重试")
    if not verify_password(body.password):
        attempts.append(now)
        raise HTTPException(401, "管理密码错误")
    _failed_attempts.pop(client, None)
    must_change = is_default_password(body.password)
    _set_cookie(
        response,
        create_session(must_change_password=must_change),
        secure=request.url.scheme == "https",
    )
    return {"ok": True, "must_change_password": must_change}


@router.post("/change-password")
def update_password(body: ChangePasswordBody, request: Request, response: Response) -> dict:
    session = get_session(request.cookies.get(SESSION_COOKIE))
    if session is None:
        raise HTTPException(401, "请先登录")
    try:
        change_password(body.current_password, body.new_password)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    _set_cookie(
        response,
        create_session(must_change_password=False),
        secure=request.url.scheme == "https",
    )
    return {"ok": True}


@router.post("/logout")
def logout(request: Request, response: Response) -> dict:
    delete_session(request.cookies.get(SESSION_COOKIE))
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"ok": True}
