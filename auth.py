"""身份相关定义。本任务只放用户上下文。"""

from pydantic import BaseModel


class UserContext(BaseModel):
    """当前请求的用户身份,由服务端 token 解析后注入图。"""

    user_id: str
