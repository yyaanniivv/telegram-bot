FROM python:3.11-slim-bookworm AS build-env

# This helps docker not rebuild unless "requirements.txt" is touched.
COPY ./requirements.txt .

# # Gcc is needed for one of the packages.
RUN apt-get update \
  && apt-get install -y --no-install-recommends gcc libssl-dev python3-dev libffi-dev\
  && rm -rf /var/lib/apt/lists/* \
  && pip install --upgrade pip \
  && pip install -r requirements.txt \
  && apt-get purge -y --auto-remove gcc libssl-dev python3-dev libffi-dev

# Create non-root user with configurable UID/GID (defaults to 1000:1000)
ARG PUID=1000
ARG PGID=1000
RUN groupadd -g "$PGID" appgroup && useradd -u "$PUID" -g "$PGID" -m appuser

COPY --chown=appuser:appgroup . /app
WORKDIR /app
ENV PYTHONUNBUFFERED=1

# Create log and output directories with correct ownership
RUN mkdir -p /app/log /app/output && chown -R appuser:appgroup /app/log /app/output

# Copy entrypoint script
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "app.py"]
