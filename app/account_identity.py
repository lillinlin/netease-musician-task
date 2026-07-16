"""账号在日志和通知中的安全展示。网页 API 仍可返回完整手机号。"""

from __future__ import annotations

from typing import Any, Mapping, Optional


def mask_phone(phone: Any) -> str:
    """手机号保留前三位和后四位，中间显示四个星号。"""
    value = str(phone or "").strip()
    if not value:
        return ""
    if len(value) >= 7:
        return f"{value[:3]}****{value[-4:]}"
    if len(value) > 2:
        return f"{value[0]}****{value[-1]}"
    return "****"


def account_label(
    account_id: Optional[int] = None,
    *,
    account: Optional[Mapping[str, Any]] = None,
    phone: Any = None,
) -> str:
    """返回“昵称（脱敏手机号）”；缺少昵称时仅返回脱敏手机号。"""
    acc = account
    if acc is None and account_id is not None:
        try:
            from app import repository as repo

            acc = repo.get_account(account_id)
        except Exception:
            acc = None

    nickname = str((acc or {}).get("nickname") or "").strip()
    masked = mask_phone((acc or {}).get("phone") or phone)
    if nickname and masked:
        return f"{nickname}（{masked}）"
    return nickname or masked or "未知账号"
