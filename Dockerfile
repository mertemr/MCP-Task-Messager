# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Install uv for fast deps
RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml ./
COPY README.md ./
COPY task_messager ./task_messager

RUN uv pip install --system -e .

ENV GOOGLE_CHAT_WEBHOOK_URL="" \
    TASK_OWNER=""

ENTRYPOINT ["python", "-m", "task_messager.server"]
