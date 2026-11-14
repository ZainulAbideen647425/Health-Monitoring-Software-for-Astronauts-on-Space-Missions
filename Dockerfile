FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir .
ENV ASTRONAUT_HEALTH_MONITOR_SECURE_COOKIES=true \
    ASTRONAUT_HEALTH_MONITOR_DATABASE_URL=sqlite:////data/astronaut_health_monitor.db \
    ASTRONAUT_HEALTH_MONITOR_ENCRYPTION_KEY_FILE=/data/.data_encryption_key
RUN mkdir -p /data
CMD ["sh", "-c", "uvicorn astronaut_health_monitor.api.application:create_application --factory --host 0.0.0.0 --port ${PORT:-8000}"]
