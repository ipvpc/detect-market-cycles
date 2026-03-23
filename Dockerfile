FROM python:3.13

ENV TZ=America/New_York \
    DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update -y && apt-get install -y \
    tzdata \
    curl \
    git \
    build-essential \
    libfreetype6-dev \
    libpng-dev \
    pkg-config \
    && rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | bash && \
    export PATH="/root/.local/bin:$PATH" && \
    uv --version

# Set up working directory
WORKDIR /workspace

# Copy requirements and install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN export PATH="/root/.local/bin:$PATH" && \
    uv pip install --system -r /tmp/requirements.txt

# Set PATH for uv
ENV PATH="/root/.local/bin:$PATH"

# Create directories for data and outputs
RUN mkdir -p /workspace/data /workspace/outputs

# Copy all Python scripts
COPY main.py /workspace/
COPY analyzer.py /workspace/
COPY app.py /workspace/
COPY db_utils.py /workspace/

# Copy static files for UI
COPY static/ /workspace/static/

# Set matplotlib backend for headless operation
ENV MPLBACKEND=Agg

# Default command (can be overridden in docker-compose)
CMD ["python", "main.py"]
