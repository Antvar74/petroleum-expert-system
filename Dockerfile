# ========== Stage 1: Build Frontend ==========
FROM node:20-alpine AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --silent
COPY frontend/ ./
RUN npm run build

# ========== Stage 2: Python Backend ==========
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
COPY utils/ ./utils/
COPY api_main.py ./

# Copy built frontend from Stage 1
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Create data directory for SQLite persistence
RUN mkdir -p /app/data

# Expose API port
EXPOSE 8000

# Run with uvicorn
CMD ["uvicorn", "api_main:app", "--host", "0.0.0.0", "--port", "8000"]
