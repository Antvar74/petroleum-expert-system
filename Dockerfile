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

# Expose API port
EXPOSE 8000

# Run with uvicorn
CMD ["uvicorn", "api_main:app", "--host", "0.0.0.0", "--port", "8000"]
