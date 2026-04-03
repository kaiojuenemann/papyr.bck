FROM python:3.12-slim

# Kein root im laufenden Container
RUN groupadd -r backup && useradd -r -g backup backup

# System-Abhängigkeiten: tar (Archivierung), curl (Healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    tar \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .
COPY templates/ templates/

# docker.sock benötigt Gruppenzugehörigkeit – wird zur Laufzeit per GID gesetzt
# (siehe docker-compose.yml: group_add)
RUN chown -R backup:backup /app

USER backup

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

CMD ["python", "-m", "gunicorn", \
     "--bind", "0.0.0.0:8080", \
     "--workers", "1", \
     "--threads", "4", \
     "--timeout", "3600", \
     "app:app"]
