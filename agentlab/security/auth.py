"""身份相关定义:demo 用户、JWT 与用户上下文。"""

import hmac
import time
from dataclasses import dataclass

import jwt
from pydantic import BaseModel

from agentlab.config import AUTH_SECRET


@dataclass(frozen=True)
class DemoUser:
    """一个合成 demo 用户。"""

    username: str
    password: str
    user_id: str


DEMO_USERS: dict[str, DemoUser] = {
    user.username: user
    for user in (
        DemoUser("alice", "alice-pass", "user_alice"),
        DemoUser("bob", "bob-pass", "user_bob"),
        DemoUser("carol", "carol-pass", "user_carol"),
    )
}


class UserContext(BaseModel):
    """当前请求的用户身份,由服务端 token 解析后注入图。"""

    user_id: str
    tenant_id: str = "tenant_a"


USER_TENANTS = {
    "user_alice": "tenant_a",
    "user_bob": "tenant_b",
    "user_carol": "tenant_c",
}


def tenant_for_user(user_id: str) -> str:
    """demo 用户到租户的固定映射；生产应由身份系统/数据库提供。"""
    return USER_TENANTS.get(user_id, "tenant_a")


def sign_token(
    user_id: str, *, secret: str | None = None, ttl_seconds: int = 3600
) -> str:
    """签发标准 HS256 JWT;payload 只放 user_id 和过期时间。"""
    key = secret if secret is not None else AUTH_SECRET
    claims = {"sub": user_id, "exp": int(time.time()) + ttl_seconds}
    return jwt.encode(claims, key, algorithm="HS256")


def verify_token(token: str, *, secret: str | None = None) -> str:
    """校验 JWT 签名和过期时间,返回 user_id;任何失败统一抛 ValueError。"""
    key = secret if secret is not None else AUTH_SECRET
    try:
        claims = jwt.decode(token, key, algorithms=["HS256"])
    except jwt.ExpiredSignatureError as exc:
        raise ValueError("token expired") from exc
    except jwt.InvalidTokenError as exc:
        raise ValueError("invalid token") from exc

    user_id = claims.get("sub")
    if not isinstance(user_id, str) or not user_id or "exp" not in claims:
        raise ValueError("invalid token payload")
    return user_id


def login(username: str, password: str) -> str | None:
    """校验 demo 用户密码,成功返回 token,失败返回 None。"""
    user = DEMO_USERS.get(username)
    if user is None or not hmac.compare_digest(user.password, password):
        return None
    return sign_token(user.user_id)
