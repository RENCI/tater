# stage 1: the build
FROM ghcr.io/astral-sh/uv:0.11.7-python3.12-trixie-slim AS builder

WORKDIR /app

# copy dep files
COPY pyproject.toml uv.lock ./

# copy package source used to install the project entrypoint
COPY tater ./tater
COPY README.md ./

# install deps into a virtual environment
RUN uv venv && . .venv/bin/activate && uv sync --locked --no-dev --no-editable


# stage 2: the final image
FROM python:3.12-slim

# environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    TATER_APP_PORT=8050

WORKDIR /app

# copy only the virtual environment from the builder; the tater package and all
# dependencies are installed inside it — no source files needed at runtime
COPY --from=builder --chown=10001:10001 /app/.venv .venv

# run as non-root in the runtime image
USER 10001:10001

# ensure the app is running with the venv python
ENV PATH="/app/.venv/bin:$PATH"

# expose the port
EXPOSE $TATER_APP_PORT

# run tater in hosted mode
CMD ["sh", "-c", "exec tater --hosted --host 0.0.0.0 --port $TATER_APP_PORT"]
