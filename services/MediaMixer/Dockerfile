FROM python:3.11-slim

WORKDIR /app
ENV PYTHONPATH=/app

# Install OpenCV dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Install xvfb for headless display
RUN apt-get update && apt-get install -y xvfb && rm -rf /var/lib/apt/lists/*

# Install ffmpeg and other dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsm6 \
    libxext6 \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY services/MediaMixer/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the MediaMixer service code
COPY services/MediaMixer/ ./services/MediaMixer/

# Expose port
EXPOSE 8080
ENV PORT=8080

# Set PYTHONPATH so imports work
ENV PYTHONPATH=/app

# Run the MediaMixer
WORKDIR /app
CMD ["python", "services/MediaMixer/media_mixer.py"]

