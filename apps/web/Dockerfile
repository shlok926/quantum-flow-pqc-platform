# ==============================================================================
# Quantum Flow Technologies — Web Frontend Dockerfile
# Multi-stage build with Node 20 builder and Nginx static server
# ==============================================================================

# Stage 1: Build static assets
FROM node:20-alpine AS builder

WORKDIR /app

# Copy root workspace manifests
COPY package.json package-lock.json* ./
COPY apps/web/package.json ./apps/web/

# Install dependencies
RUN npm ci

# Copy web app source code
COPY apps/web ./apps/web

# Build production bundle
WORKDIR /app/apps/web
RUN npm run build

# Stage 2: Serve with lightweight Nginx
FROM nginx:alpine AS runner

COPY infra/docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/apps/web/dist /usr/share/nginx/html

EXPOSE 3000

HEALTHCHECK --interval=30s --timeout=3s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1:3000/ || exit 1

CMD ["nginx", "-g", "daemon off;"]

