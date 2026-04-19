FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml /app/pyproject.toml
COPY src /app/src
COPY knowledge /app/knowledge
COPY skills /app/skills

RUN pip install --no-cache-dir --upgrade pip && pip install --no-cache-dir .

EXPOSE 8080

CMD ["music-agent-serve"]
