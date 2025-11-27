# --- stage 1 - build ---
FROM node:current-alpine AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
ENV UV_PYTHON_INSTALL_DIR=/app/python-bin UV_PYTHON_PREFERENCE=only-managed
WORKDIR /app
COPY ../ .
RUN \
  apk add --no-cache uv && \
  uv sync && \
  ## Workaround for the error at build time reported in https://github.com/loganrooks/zlibrary-mcp/issues/8
  uv pip compile pyproject.toml -o requirements.txt && \
  npm install && \
  npm run build

# --- stage 2 - runtime ---
FROM ghcr.io/supercorp-ai/supergateway:3.4.3 AS runner

WORKDIR /app

COPY --from=builder /app/python-bin ./python-bin/
COPY --from=builder /app/.venv ./.venv/
COPY --from=builder /app/zlibrary ./zlibrary/
COPY --from=builder /app/dist ./dist/
COPY --from=builder /app/node_modules ./node_modules/
COPY --from=builder /app/lib ./lib/


