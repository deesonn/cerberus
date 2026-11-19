FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv

# Runtime dependencies only (pytest/httpx are for tests, not the image).
COPY requirements.txt .
RUN grep -Ev '^(pytest|httpx)$' requirements.txt > requirements.runtime.txt \
    && pip install --no-cache-dir -r requirements.runtime.txt

COPY app ./app

# Run as a normal user. The database lives in /data, which docker-compose mounts as a volume.
RUN useradd --create-home cerberus && mkdir /data && chown cerberus /data
USER cerberus
ENV CERBERUS_DB_URL=sqlite:////data/cerberus.db
VOLUME /data

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
