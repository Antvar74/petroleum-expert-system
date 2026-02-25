# ========== PetroExpert Backend ==========
# Frontend is built separately in nginx/Dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend source code
COPY agents/ ./agents/
COPY config/ ./config/
COPY knowledge_base/ ./knowledge_base/
COPY middleware/ ./middleware/
COPY models/ ./models/
COPY orchestrator/ ./orchestrator/
COPY routes/ ./routes/
COPY utils/ ./utils/
COPY api_main.py ./

# Create data directory for SQLite persistence
RUN mkdir -p /app/data

# Copy schemas
COPY schemas/ ./schemas/

# Create non-root user and set ownership
RUN addgroup --gid 1001 appgroup && \
    adduser --uid 1001 --ingroup appgroup --disabled-password --no-create-home appuser && \
    chown -R appuser:appgroup /app

USER appuser

# Expose API port
EXPOSE 8000

# Run with Gunicorn + Uvicorn workers for production
# WEB_CONCURRENCY controls worker count (default: 4)
CMD ["gunicorn", "api_main:app", \
     "--bind", "0.0.0.0:8000", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--timeout", "300", \
     "--graceful-timeout", "30"]
