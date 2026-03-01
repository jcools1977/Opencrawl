FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements-cloud.txt .
RUN pip install --no-cache-dir -r requirements-cloud.txt

# Copy application code
COPY convoyield/ convoyield/
COPY cloud/ cloud/
COPY pyproject.toml .

# Install the package itself (for imports)
RUN pip install --no-cache-dir -e .

# Cloud Run injects PORT env var (default 8080)
ENV PORT=8080

EXPOSE ${PORT}

CMD ["python", "-c", "from cloud.server import main; main()"]
