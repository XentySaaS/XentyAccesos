# SPA en modo dev (Vite). El proxy /api se configura con VITE_PROXY_TARGET (servicio del compose).
FROM node:20-alpine

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
