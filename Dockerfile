FROM python:3.12-slim

# Install essential build tools
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc python3-dev curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Use absolute path for requirements
COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy all files with proper ownership
COPY --chown=1000:1000 . /app

# Ensure correct Python path
ENV PYTHONPATH=/app \
    PYTHONUNBUFFERED=1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]