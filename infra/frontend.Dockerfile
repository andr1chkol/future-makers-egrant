FROM node:22-bookworm-slim
WORKDIR /workspace/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
CMD ["npm", "run", "dev"]
