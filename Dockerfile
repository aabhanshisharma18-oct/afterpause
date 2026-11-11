FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
RUN groupadd --gid 10001 museum && useradd --uid 10001 --gid museum --create-home museum
COPY --chown=museum:museum . .
RUN mkdir -p /data/uploads /app/instance && chown -R museum:museum /data /app/instance
ENV APP_ENV=production UPLOAD_DIR=/data/uploads PORT=8000
USER museum
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/healthz', timeout=3)"
CMD ["sh", "scripts/start-production.sh"]
