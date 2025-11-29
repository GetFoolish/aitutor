# -----------------------------------------------
# Stage 1: Base Python image
# -----------------------------------------------
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# -----------------------------------------------
# Stage 2: System dependencies
# -----------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------------------------
# Stage 3: Python dependencies
# -----------------------------------------------
# Copy only requirements first for caching
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# -----------------------------------------------
# Stage 4: Copy the application code
# -----------------------------------------------
# Copy managers directory (needed for MongoDB and config)
COPY managers/ ./managers/

# Copy shared directory (needed for authentication)
COPY shared/ ./shared/

# Copy services directory
COPY services/ ./services/

# Copy config.json
COPY config.json .

# -----------------------------------------------
# Stage 5: Expose port and start server
# -----------------------------------------------
EXPOSE 8080
ENV PORT=8080

CMD ["python", "-m", "services.DashSystem.dash_api"]

