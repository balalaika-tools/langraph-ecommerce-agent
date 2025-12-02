FROM python:3.13-slim-bookworm AS base
WORKDIR /app

############################
# Builder: Install dependencies with uv
############################
FROM base AS builder

# Copy uv binary into builder
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set uv config for stability
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Copy dependency files
COPY pyproject.toml uv.lock ./ 

# Install dependencies (cached layer)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Copy code and optional index
COPY src/ ./src/


# Install your app into the venv
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

############################
# Runner: Clean, minimal image
############################
FROM base AS runner

# Copy only the built app and venv
COPY --from=builder /app /app
ENV PATH="/app/.venv/bin:$PATH"

# Create group/user WITH home dir and set HOME
RUN groupadd -r app \
 && useradd -m -r -g app -d /home/app app \
 && chown -R app:app /home/app /app
ENV HOME=/home/app

USER app
EXPOSE 8000

# Default command
CMD ["gunicorn", "-k", "uvicorn.workers.UvicornWorker", "-w", "1", "-b", "0.0.0.0:8000", "--access-logfile", "-", "analyst_9000.main:run_app"]