# Base stage
FROM python:3.11-slim as base

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Development stage
FROM base as development

# Install development dependencies
COPY requirements-dev.txt .
RUN pip install -r requirements-dev.txt

# Copy application code
COPY . .
COPY ./wait-for-it.sh /
COPY ./docker-entrypoint.sh /
RUN chmod +x /wait-for-it.sh
RUN chmod +x /docker-entrypoint.sh

# Set environment for development
ENV FLASK_ENV=development
ENV APP_MODE=development
ENV WAIT_FOR_DB=true
ENV RUN_MIGRATIONS=true

EXPOSE 5000
ENTRYPOINT ["/docker-entrypoint.sh"]

# Production stage
FROM base as production

# Copy application code (no dev dependencies)
COPY . .
COPY ./wait-for-it.sh /
COPY ./docker-entrypoint.sh /
RUN chmod +x /wait-for-it.sh
RUN chmod +x /docker-entrypoint.sh

# Install Gunicorn for production
RUN pip install gunicorn

# Set environment for production
ENV FLASK_ENV=production
ENV APP_MODE=production
ENV WAIT_FOR_DB=true
ENV RUN_MIGRATIONS=true

EXPOSE 5000
ENTRYPOINT ["/docker-entrypoint.sh"]