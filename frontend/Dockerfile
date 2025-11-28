FROM node:18-alpine as builder

WORKDIR /app
ARG VITE_DASH_API_URL
ARG VITE_SHERLOCKED_API_URL
ARG VITE_TEACHING_ASSISTANT_API_URL
ARG VITE_TUTOR_WS

# Set as environment variables for the build
ENV VITE_DASH_API_URL=$VITE_DASH_API_URL
ENV VITE_SHERLOCKED_API_URL=$VITE_SHERLOCKED_API_URL
ENV VITE_TEACHING_ASSISTANT_API_URL=$VITE_TEACHING_ASSISTANT_API_URL
ENV VITE_TUTOR_WS=$VITE_TUTOR_WS

# Copy package files
COPY frontend/package*.json ./
RUN npm install --legacy-peer-deps

# Copy source
COPY frontend/ ./

# Build the app
RUN npm run build

# Production image with nginx
FROM nginx:alpine

# Copy built files
COPY --from=builder /app/build /usr/share/nginx/html

# Copy nginx config
RUN echo 'server { \
    listen 8080; \
    server_name _; \
    root /usr/share/nginx/html; \
    index index.html; \
    location / { \
        try_files $uri $uri/ /index.html; \
    } \
    gzip on; \
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml application/xml+rss text/javascript; \
}' > /etc/nginx/conf.d/default.conf

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]

