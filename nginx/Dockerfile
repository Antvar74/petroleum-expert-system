# ========== Stage 1: Build React Frontend ==========
FROM node:20-alpine AS build

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --silent
COPY frontend/ ./
RUN npm run build

# ========== Stage 2: Nginx ==========
FROM nginx:alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy our config
COPY nginx/nginx.conf /etc/nginx/conf.d/default.conf

# Copy built frontend from Stage 1
COPY --from=build /app/dist /usr/share/nginx/html

# Run as non-root nginx user
RUN chown -R nginx:nginx /usr/share/nginx/html && \
    chown -R nginx:nginx /var/cache/nginx && \
    chown -R nginx:nginx /var/log/nginx && \
    touch /var/run/nginx.pid && chown nginx:nginx /var/run/nginx.pid

USER nginx

EXPOSE 80 443

CMD ["nginx", "-g", "daemon off;"]
