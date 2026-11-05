# Stage 1 — build the Vue app on Node 24 (Active LTS)
FROM node:24-alpine AS builder
WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./
# Basemap: hosted (OpenFreeMap, default) | none. A self-hosted PMTiles file takes precedence,
# e.g. --build-arg VITE_PMTILES_URL=/tiles/canada.pmtiles
ARG VITE_BASEMAP=hosted
ARG VITE_PMTILES_URL=""
ENV VITE_BASEMAP=$VITE_BASEMAP
ENV VITE_PMTILES_URL=$VITE_PMTILES_URL
RUN npm run build

# Stage 2 — serve with nginx
# Pinned stable line (Dependabot bumps tag and digest together)
FROM nginx:1.31.8-alpine@sha256:785835ea65db4bba6f021acc0f3be91b0fef76a53fe41f8588c6698d2aed0606 AS runtime
# The digest pin lags Alpine's security fixes (the image scan fails on any fixable HIGH), so pull them in
RUN apk upgrade --no-cache
COPY --from=builder /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
