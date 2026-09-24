# Stage 1 — build the Vue app on Node 24 (Active LTS)
FROM node:25-alpine AS builder
WORKDIR /app

COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund

COPY frontend/ ./
# Optional self-hosted basemap, e.g. --build-arg VITE_PMTILES_URL=/tiles/canada.pmtiles
ARG VITE_PMTILES_URL=""
ENV VITE_PMTILES_URL=$VITE_PMTILES_URL
RUN npm run build

# Stage 2 — serve with nginx
FROM nginx:alpine AS runtime
COPY --from=builder /app/dist /usr/share/nginx/html
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
