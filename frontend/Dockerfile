ARG NODE_BASE_IMAGE=node:22-alpine
FROM ${NODE_BASE_IMAGE} AS base

WORKDIR /app
COPY package*.json ./
RUN npm ci

COPY . .

FROM base AS development
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]

FROM base AS production
RUN npm run build
