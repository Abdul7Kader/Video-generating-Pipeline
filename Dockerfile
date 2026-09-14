FROM node:22-bookworm-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_BREAK_SYSTEM_PACKAGES=1 \
    HOME=/home/pipeline

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip ffmpeg ca-certificates \
    libnss3 libdbus-1-3 libatk1.0-0 libgbm-dev libasound2 \
    libxrandr2 libxkbcommon-dev libxfixes3 libxcomposite1 libxdamage1 \
    libatk-bridge2.0-0 libpango-1.0-0 libcairo2 libcups2 \
    fonts-noto-core fonts-noto-color-emoji \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

COPY renderer/package.json renderer/package-lock.json ./renderer/
RUN cd renderer && npm ci && npx remotion browser ensure

COPY backend ./backend
COPY renderer ./renderer
COPY web ./web
COPY scripts ./scripts
COPY README.md ./

RUN groupadd --gid 10001 pipeline \
    && useradd --uid 10001 --gid 10001 --home-dir /home/pipeline pipeline \
    && mkdir -p /data /home/pipeline \
    && chown -R pipeline:pipeline /data /home/pipeline /app

USER pipeline
EXPOSE 8080
CMD ["python3", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8080", "--proxy-headers", "--no-server-header"]
