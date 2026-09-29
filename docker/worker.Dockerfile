FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ffmpeg \
        libsndfile1 \
        build-essential \
        git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-worker.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements-worker.txt

COPY . .

RUN mkdir -p /app/data/input /app/data/output
