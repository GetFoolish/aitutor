FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY services/Tutor/package*.json ./

# Install dependencies
RUN npm install

# Copy service code (this copies all files and subdirectories including system_prompts)
COPY services/Tutor/ ./

# Explicitly verify system_prompts directory and file are present
RUN if [ ! -d "system_prompts" ]; then \
      echo "ERROR: system_prompts directory not found!" && exit 1; \
    fi && \
    if [ ! -f "system_prompts/adam_tutor.md" ]; then \
      echo "ERROR: system_prompts/adam_tutor.md file not found!" && exit 1; \
    else \
      echo "✓ system_prompts directory and adam_tutor.md file verified"; \
    fi

# Expose port
EXPOSE 8080
ENV PORT=8080

# Run the server
CMD ["node", "server.js"]

