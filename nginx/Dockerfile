# ============================================================
# HEALTH-BRIDGE Nginx — Builds frontend + serves via nginx
# ============================================================
# Stage 1: Build React/Vite frontend
# Stage 2: Copy built assets into nginx + add proxy config
# ============================================================

# --- Stage 1: Frontend build ---
FROM node:20-alpine AS frontend-builder

WORKDIR /app

# Install deps first (cached unless package.json changes)
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

# Copy source
COPY frontend/ .

# Vite bakes env vars at build time.
# VITE_API_URL="" tells api.js to use relative "/api" path (nginx proxies it).
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL

# Firebase config (public client keys — safe as build args)
ARG VITE_FIREBASE_API_KEY
ARG VITE_FIREBASE_AUTH_DOMAIN
ARG VITE_FIREBASE_PROJECT_ID
ARG VITE_FIREBASE_STORAGE_BUCKET
ARG VITE_FIREBASE_MESSAGING_SENDER_ID
ARG VITE_FIREBASE_APP_ID
ARG VITE_FIREBASE_MEASUREMENT_ID

ENV VITE_FIREBASE_API_KEY=$VITE_FIREBASE_API_KEY
ENV VITE_FIREBASE_AUTH_DOMAIN=$VITE_FIREBASE_AUTH_DOMAIN
ENV VITE_FIREBASE_PROJECT_ID=$VITE_FIREBASE_PROJECT_ID
ENV VITE_FIREBASE_STORAGE_BUCKET=$VITE_FIREBASE_STORAGE_BUCKET
ENV VITE_FIREBASE_MESSAGING_SENDER_ID=$VITE_FIREBASE_MESSAGING_SENDER_ID
ENV VITE_FIREBASE_APP_ID=$VITE_FIREBASE_APP_ID
ENV VITE_FIREBASE_MEASUREMENT_ID=$VITE_FIREBASE_MEASUREMENT_ID

RUN npm run build

# --- Stage 2: Nginx ---
FROM nginx:alpine

# Copy built frontend assets
COPY --from=frontend-builder /app/dist /usr/share/nginx/html

# Copy nginx config
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
