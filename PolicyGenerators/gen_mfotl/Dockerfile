# Use official Python image as base
FROM python:3.9-slim AS builder

# Set build arguments (configurable at build time)
ARG REPO_URL="https://git.ku.dk/krq770/monitoring_benchmark_generator.git"
ARG BRANCH="main"
ARG REPO_DIR="/app"

# Set environment variables for runtime
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends git build-essential && rm -rf /var/lib/apt/lists/*

RUN useradd -m appuser
WORKDIR ${REPO_DIR}
RUN chown appuser:appuser ${REPO_DIR}
USER appuser

# Clone repository
WORKDIR ${REPO_DIR}
RUN git clone --branch ${BRANCH} --depth 1 ${REPO_URL} .

# Install Python dependencies
RUN pip install pandas
RUN pip install argparse

# Create runtime image
FROM python:3.9-slim

# Set runtime arguments
ARG REPO_DIR="/app"

# Create and use non-root user
RUN useradd -m appuser
WORKDIR ${REPO_DIR}
RUN chown appuser:appuser ${REPO_DIR}
USER appuser

# Copy installed Python packages from builder
COPY --from=builder --chown=appuser:appuser /home/appuser/.local /home/appuser/.local

# Ensure scripts in .local are usable
ENV PATH=/home/appuser/.local/bin:$PATH

# Copy application code
COPY --from=builder --chown=appuser:appuser ${REPO_DIR} ${REPO_DIR}

# Set default command to run the tool
ENTRYPOINT ["generator"]
