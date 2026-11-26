"""登录请求与响应模型。"""

from pydantic import BaseModel


class LoginRequest(BaseModel):
    """登录请求。"""

    username: str
    password: str


class LoginResponse(BaseModel):
    """登录响应。"""

    token: str
