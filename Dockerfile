FROM docker.io/python:3.11-alpine

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir flask

# Copy application files
COPY app/ ./app/
COPY templates/ ./templates/
COPY static/ ./static/

# Create data directory for SQLite
RUN mkdir -p /app/data

WORKDIR /app/app

# Initialize database with sample data
RUN python seed_data.py

EXPOSE 5000

CMD ["python", "app.py"]
