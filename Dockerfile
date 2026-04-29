FROM python:3.10-slim

# Prevent Python from buffering output
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Copy dependencies
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy entire project
COPY . .

# Cloud Run expects port 8080
ENV PORT=8080

# Run with Gunicorn (production server)
CMD ["gunicorn", "-b", "0.0.0.0:8080", "run:app", "--timeout", "180", "--workers", "1", "--threads", "2"]