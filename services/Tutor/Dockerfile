FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY services/Tutor/package*.json ./

# Install dependencies
RUN npm install

# Copy service code files
COPY services/Tutor/server.js ./

# Explicitly copy system_prompts directory to ensure it's included
# (Important: .gitignore has *.md which might exclude it from git-based builds)
COPY services/Tutor/system_prompts/ ./system_prompts/

# Explicitly verify system_prompts directory and file are present
RUN if [ ! -d "system_prompts" ]; then \
      echo "ERROR: system_prompts directory not found!" && exit 1; \
    fi && \
    if [ ! -f "system_prompts/adam_tutor.md" ]; then \
      echo "ERROR: system_prompts/adam_tutor.md file not found!" && exit 1; \
    else \
      echo "✓ system_prompts directory and adam_tutor.md file verified"; \
      ls -la system_prompts/; \
    fi

# Expose port
EXPOSE 8080
ENV PORT=8080

# Run the server
CMD ["node", "server.js"]

