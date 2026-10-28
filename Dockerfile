FROM docker.m.daocloud.io/library/python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    UV_HTTP_TIMEOUT=300

# 需要换 PyPI 镜像时:--build-arg PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple
ARG PIP_INDEX_URL=https://pypi.org/simple
RUN pip install --no-cache-dir --index-url "$PIP_INDEX_URL" uv

WORKDIR /app

# 先装依赖,利用镜像层缓存;AgentLab 运行时需要 serve/observability/rag/mcp 组
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project \
    --group serve --group observability --group rag --group mcp

COPY . .
RUN uv sync --frozen --no-dev \
    --group serve --group observability --group rag --group mcp

EXPOSE 8000
CMD ["uv", "run", "--no-sync", "agentlab-api"]
