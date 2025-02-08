ARG DEBIAN_VERSION=bookworm
ARG UV_VERSION=0.5.4
ARG VARIANT=3.12


FROM ghcr.io/astral-sh/uv:$UV_VERSION AS uv


FROM python:$VARIANT-slim-$DEBIAN_VERSION
LABEL maintainer="yu-min <>"

ENV PYTHONDONTWRITEBYTECODE=True
ENV PYTHONUNBUFFERED=True
ENV UV_LINK_MODE=copy

WORKDIR /app

COPY --from=uv /uv /uvx /bin/
COPY pyproject.toml uv.lock ./
COPY src/ ./src/
COPY app.py ./

RUN uv sync --frozen --no-install-project


# ポートとエントリポイントを指定
EXPOSE 8080
CMD ["uv","run","chainlit", "run", "app.py","--host","0.0.0.0", "--port", "8080"]
