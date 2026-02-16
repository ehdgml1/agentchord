FROM node:20-alpine AS frontend-builder

WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY index.html tsconfig*.json vite.config.ts postcss.config.js tailwind.config.js ./
COPY src/ ./src/
COPY public/ ./public/
RUN npm run build

FROM nginx:alpine

RUN rm /etc/nginx/conf.d/default.conf
COPY nginx/nginx.conf /etc/nginx/conf.d/
COPY --from=frontend-builder /app/dist /usr/share/nginx/html

# Ensure nginx user has access to required directories
RUN chown -R nginx:nginx /usr/share/nginx/html /var/cache/nginx /var/log/nginx /etc/nginx/conf.d && \
    chmod -R 755 /usr/share/nginx/html

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1

# L4: Run as non-root user for security
USER nginx
