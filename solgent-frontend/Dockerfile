# ---- Stage 1: build the static bundle ------------------------------------
FROM node:20-alpine AS builder

WORKDIR /build

# Copy lockfile + package.json first so Docker's layer cache is invalidated
# only when dependencies actually change, not on every source edit.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .
RUN npm run build

# ---- Stage 2: serve the static bundle ------------------------------------
FROM nginx:1.27-alpine AS runtime

COPY --from=builder /build/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]