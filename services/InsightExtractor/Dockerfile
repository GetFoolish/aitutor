FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY services/InsightExtractor/requirements.txt ./services/InsightExtractor/
COPY requirements.txt ./

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install --no-cache-dir -r services/InsightExtractor/requirements.txt

# Copy application code
COPY shared/ ./shared/
COPY managers/ ./managers/
COPY services/InsightExtractor/ ./services/InsightExtractor/
COPY services/__init__.py ./services/

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8004

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8004/health || exit 1

# Run the service
CMD ["python", "-m", "uvicorn", "services.InsightExtractor.main:app", "--host", "0.0.0.0", "--port", "8004"]
