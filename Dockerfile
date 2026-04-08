ARG UV_BASE_IMAGE=ghcr.io/astral-sh/uv:0.8.15-python3.12-bookworm-slim

# stage 1: the build
FROM ${UV_BASE_IMAGE} AS builder

WORKDIR /app

# copy dep files
COPY pyproject.toml uv.lock ./

# copy package source used to install the project entrypoint
COPY tater ./tater
COPY README.md ./

# install deps
RUN uv venv && . .venv/bin/activate && uv sync --locked --no-dev


# stage 2: the final image
# Use the same base family as the builder so the copied venv remains valid.
FROM ${UV_BASE_IMAGE}

# environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8050

WORKDIR /app

# copy the virtual environment from the builder stage
COPY --from=builder --chown=10001:10001 /app/.venv .venv

# copy the application code from the builder stage
COPY --from=builder --chown=10001:10001 /app .

# run as non-root in the runtime image
USER 10001:10001

# ensure the app is running with the venv python
ENV PATH="/app/.venv/bin:$PATH"

# expose the port
EXPOSE $PORT

# run tater in hosted mode
CMD ["sh", "-c", "exec tater --hosted --host 0.0.0.0 --port ${PORT:-8050}"]