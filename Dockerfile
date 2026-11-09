FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 SERVICEHUB_HOST=0.0.0.0 SERVICEHUB_PORT=8000 SERVICEHUB_DB_PATH=/data/servicehub.db
WORKDIR /app
COPY . /app
RUN mkdir -p /data /app/static/uploads && useradd --system --uid 10001 --home-dir /app servicehub && chown -R servicehub:servicehub /app /data
USER servicehub
EXPOSE 8000
VOLUME ["/data", "/app/static/uploads"]
CMD ["python", "server.py"]
