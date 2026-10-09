FROM python:3.11-slim-bookworm@sha256:8dca233de9f3d9bb410665f00a4da6dd06f331083137e0e98ccf227236fcc438
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 libgl1 libxrender1 libxext6 libglib2.0-0 libgomp1 \
    && rm -rf /var/lib/apt/lists/*
ENV UV_PROJECT_ENVIRONMENT=/opt/venv UV_LINK_MODE=copy
RUN pip install --no-cache-dir uv==0.12.24
WORKDIR /opt/cad
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
ENV PATH="/opt/venv/bin:$PATH" PYTHONPATH=/workspace/src PYTHONUNBUFFERED=1
WORKDIR /workspace
CMD ["python", "-m", "machine_cad", "build"]
