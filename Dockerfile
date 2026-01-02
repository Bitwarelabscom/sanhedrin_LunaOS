# Sanhedrin Docker Image
# Multi-stage build for optimal size

# Build stage
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY pyproject.toml README.md ./
COPY src/ ./src/

RUN pip install --no-cache-dir build && \
    python -m build --wheel


# Production stage
FROM python:3.11-slim as production

# Install Node.js for Claude Code CLI
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Claude Code CLI
RUN npm install -g @anthropic-ai/claude-code

# Security: Create non-root user
RUN groupadd --gid 1000 sanhedrin && \
    useradd --uid 1000 --gid sanhedrin --shell /bin/bash --create-home sanhedrin && \
    mkdir -p /home/sanhedrin/.claude && \
    chown -R sanhedrin:sanhedrin /home/sanhedrin

WORKDIR /app

# Install sanhedrin with extras
COPY --from=builder /app/dist /dist

RUN pip install --no-cache-dir "/dist/sanhedrin-0.1.0-py3-none-any.whl[server,cli]" httpx && \
    rm -rf /dist

# Security: Run as non-root user
USER sanhedrin

# Environment configuration
ENV SANHEDRIN_HOST=0.0.0.0 \
    SANHEDRIN_PORT=8000 \
    SANHEDRIN_ENV=production \
    SANHEDRIN_LOG_LEVEL=INFO \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health').raise_for_status()" || exit 1

# Expose port
EXPOSE 8000

# Run server
CMD ["python", "-m", "sanhedrin.cli.main", "serve"]
