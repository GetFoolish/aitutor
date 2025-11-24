# -----------------------------------------------
# Stage 1: Base Python image
# -----------------------------------------------
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# -----------------------------------------------
# Stage 2: Install system dependencies
# -----------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# -----------------------------------------------
# Stage 3: Install Python dependencies
# -----------------------------------------------
# Copy only requirements file first for caching
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# -----------------------------------------------
# Stage 4: Copy all SherlockED API source code
# -----------------------------------------------
# Copy managers directory (needed for MongoDB)
COPY managers/ ./managers/

# Copy services directory
COPY services/ ./services/

# Copy config.json
COPY config.json .

# -----------------------------------------------
# Stage 5: Expose port and start server
# -----------------------------------------------
EXPOSE 8080
ENV PORT=8080

CMD ["python", "services/SherlockEDApi/run_backend.py"]

