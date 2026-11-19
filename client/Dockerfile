# Stage 1: build the Angular app
FROM node:22-slim AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npx ng build

# Stage 2: serve the static files with nginx and forward /api to the backend
FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/client/browser /usr/share/nginx/html
EXPOSE 80
