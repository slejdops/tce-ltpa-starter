# Python 3.6 base image (EOL). If unavailable in your registry, switch to 3.8/3.9 and keep app code the same.
FROM python:3.6-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps (add ca-certificates for TLS to DASH)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Install requirements first for better layer caching
COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY tce_app ./tce_app
COPY run.py ./run.py

EXPOSE 5000

# Set sane defaults (override at runtime)
ENV FLASK_RUN_HOST=0.0.0.0 \
    FLASK_RUN_PORT=5000 \
    VERIFY_TLS=true \
    TIMEOUT_SECONDS=5 \
    LTPA_TOKEN_NAME=LtpaToken2

CMD ["python", "run.py"]
