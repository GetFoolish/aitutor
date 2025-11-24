FROM node:18-alpine

WORKDIR /app

# Copy package files
COPY services/Tutor/package*.json ./

# Install dependencies
RUN npm install

# Copy service code
COPY services/Tutor/ ./

# Expose port
EXPOSE 8080
ENV PORT=8080

# Run the server
CMD ["node", "server.js"]

