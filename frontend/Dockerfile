FROM node:24-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# "/" = same-origin via the nginx /api proxy (docker-compose).
# Fly overrides this at build time with the public API URL (see fly.toml).
ARG VITE_API_BASE=/
ENV VITE_API_BASE=$VITE_API_BASE
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
# Template is rendered by the nginx image entrypoint (envsubst) at start,
# so API_UPSTREAM / NGINX_RESOLVER can differ per platform without a rebuild.
COPY nginx.conf /etc/nginx/templates/default.conf.template
ENV API_UPSTREAM=api:8000 \
    NGINX_RESOLVER=127.0.0.11
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
