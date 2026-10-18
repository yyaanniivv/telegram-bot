# Magnet2Torrent Telegram Bot

Telegram bot which accepts magnet links and turns them into `.torrent` files locally.

## Building & Deploying (Multi-Arch)

### One-time Setup

```bash
# Create a BuildKit builder with QEMU for cross-compilation
docker buildx create --name multiarch --driver docker-container --use
docker buildx inspect --bootstrap
```

### Build & Push Multi-Arch Image

```bash
# Build for AMD64 + ARM64 and push to registry
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t yyaanniivv/telegram-bot:buildx-latest \
  --push \
  .
```

### Local Build (Single Arch)

```bash
# Quick local build for current architecture
docker compose build
# or
docker build -t yyaanniivv/telegram-bot:local .
```

### Run with Docker Compose

```bash
# Requires .env with TELEGRAM_TOKEN, APPROVED_IDS, SEARCH_URL, etc.
docker compose up -d
```

## Development

### Python Environment

```bash
# Requires pyenv + pyenv-virtualenv
pyenv install 3.11.9
pyenv virtualenv 3.11.9 telegram-bot
pyenv activate telegram-bot
pip install -r requirements.txt
pip install pytest
```

### Run Tests

```bash
PYTHONPATH=. pytest tests/ -v
```

### Run Locally

```bash
cp .env.example .env
# Edit .env with your credentials
python app.py
```

## Release Process

The CD pipeline (`.github/workflows/cd.yml`) triggers on **semantic version tags** (`v*`):

```bash
# 1. Merge changes to main (CI runs automatically)
git push origin main

# 2. When ready to release, tag and push
git tag v1.0.0
git push origin v1.0.0
```

This builds & pushes a multi-arch image (`linux/amd64,linux/arm64`) to Docker Hub as `yyaanniivv/telegram-bot:v1.0.0` and `yyaanniivv/telegram-bot:latest`, then runs a Trivy vulnerability scan.

**Required GitHub Secrets** (Settings → Secrets → Actions):
- `DOCKERHUB_USERNAME`
- `DOCKERHUB_TOKEN`

---

## Tech Stack

- **Python**: 3.11.9
- **Telegram**: python-telegram-bot 22.x
- **HTTP**: urllib3 2.8.x
- **Deployment**: Docker multi-stage, multi-arch via buildx
- **CI/CD**: GitHub Actions (lint, test, audit, multi-arch build, Trivy scan)