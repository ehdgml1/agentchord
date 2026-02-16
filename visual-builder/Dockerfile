# ============================================
# Stage 1: Frontend build
# ============================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app

# Copy package files for caching
COPY package.json package-lock.json ./
RUN npm ci

# Copy frontend source and build
COPY index.html tsconfig*.json vite.config.ts postcss.config.js tailwind.config.js ./
COPY src/ ./src/
COPY public/ ./public/
RUN npm run build

# ============================================
# Stage 2: Backend runtime
# ============================================
FROM python:3.11-slim AS backend

# Security: run as non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl && \
    rm -rf /var/lib/apt/lists/*

# L8: Copy and install Python dependencies with optimizations
COPY backend/requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend application
COPY backend/app/ ./app/
COPY backend/gunicorn.conf.py ./
COPY backend/alembic.ini ./
COPY backend/alembic/ ./alembic/
COPY backend/test_db_init.py ./

# Copy docker entrypoint script
COPY backend/docker-entrypoint.sh /docker-entrypoint.sh

# Copy frontend build for static serving
COPY --from=frontend-builder /app/dist ./static/

# Set ownership and make entrypoint executable
RUN chown -R appuser:appuser /app && \
    chmod +x /docker-entrypoint.sh

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

EXPOSE 8000

# Set entrypoint to run migrations before starting
ENTRYPOINT ["/docker-entrypoint.sh"]

# Production server
CMD ["gunicorn", "-c", "gunicorn.conf.py", "app.main:app"]
