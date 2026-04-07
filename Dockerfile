# STAGE 1: the build
FROM containers.renci.org/helxplatform/uv-base:v0.0.1 AS builder

# environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

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
FROM containers.renci.org/helxplatform/uv-base:v0.0.1

# environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8050 \
    DASH_ENV=production

WORKDIR /app

# copy the virtual environment from the builder stage
COPY --from=builder /app/.venv .venv

# copy the application code from the builder stage
COPY --from=builder /app .

# ensure the app is running with the venv python
ENV PATH="/app/.venv/bin:$PATH"

# expose the port
EXPOSE $PORT

# run tater in hosted mode
CMD ["tater", "--hosted", "--host", "0.0.0.0", "--port", "8050"]