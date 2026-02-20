# syntax=docker/dockerfile:1

ARG PYTHON_VERSION=3.12
ARG ALPINE_VERSION=3.23
ARG UV_VERSION=latest

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM python:${PYTHON_VERSION}-alpine${ALPINE_VERSION} AS builder

COPY --from=uv /uv /bin/

ENV UV_PROJECT_ENVIRONMENT=/usr/local \
    UV_LINK_MODE=copy \
    UV_LOCKED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_NO_EDITABLE=1 \
    UV_NO_CONFIG=0

COPY pyproject.toml uv.lock ./

RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project --no-dev

FROM python:${PYTHON_VERSION}-alpine${ALPINE_VERSION} AS base

ARG PYTHON_VERSION

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN addgroup -g 1000 -S appgroup && \
    adduser -u 1000 -S appuser -G appgroup

COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /usr/local/lib/python${PYTHON_VERSION} /usr/local/lib/python${PYTHON_VERSION}

COPY --chown=1000:1000 . .

ENV GOOGLE_CHAT_WEBHOOK_URL="" \
    TASK_OWNER=""

EXPOSE 8000

CMD ["python", "-m", "task_messager.server"]

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD wget --no-verbose --spider http://localhost:8000 || exit 1
