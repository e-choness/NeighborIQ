# Stage 1 — Build the Vue 3 app
FROM node:18-alpine AS builder
WORKDIR /app

# Copy dependency manifests and install
COPY frontend/package.json ./
RUN npm install

# Copy source and build
COPY frontend/ ./
RUN npm run build

# Stage 2 — Serve with nginx
FROM nginx:alpine AS runtime
# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html
# Copy nginx configuration
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
# Remove the default nginx config
RUN rm -f /etc/nginx/conf.d/default.conf.bak

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
