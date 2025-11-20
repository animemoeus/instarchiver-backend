# Instarchiver Backend

A Django REST API backend for archiving Instagram content and managing user data.

[![codecov](https://codecov.io/github/instarchiver/instarchiver-backend/graph/badge.svg?token=qLvch7qoAF)](https://codecov.io/github/instarchiver/instarchiver-backend)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
![Uptime Robot status](https://img.shields.io/uptimerobot/status/m801829955-01095d331ccf91d3ab2297bc)
![Uptime Robot ratio (7 days)](https://img.shields.io/uptimerobot/ratio/7/m801829955-01095d331ccf91d3ab2297bc)


License: MIT

## Overview

Instarchiver is a backend service that provides APIs for archiving Instagram content. Built with Django and Django REST Framework, it offers user authentication, content management, and data export capabilities.

## Features

- **Instagram User Management**: Archive and track Instagram user profiles with historical data
- **User History Tracking**: Automatic versioning of user profile changes
- **RESTful API**: Comprehensive endpoints with filtering, search, and pagination
- **Caching**: Redis-based caching for improved performance
- **Authentication**: JWT-based user authentication and management
- **Background Processing**: Celery task queue for async operations
- **API Documentation**: Interactive Swagger/OpenAPI documentation
- **Docker Support**: Full containerization for development and production
- **Code Coverage**: Automated testing with coverage reporting via Codecov

## Technology Stack

- **Django 5.1** - Web framework
- **Django REST Framework** - API development
- **PostgreSQL** - Primary database
- **Redis** - Caching and session storage
- **Celery** - Background task processing
- **Docker** - Containerization
- **Gunicorn** - WSGI server

## Quick Start

### Prerequisites

- Python 3.12+
- PostgreSQL
- Redis
- Docker & Docker Compose (recommended)
- Just (optional, for task automation)

### Docker Development (Recommended)

The easiest way to get started is using Docker Compose with Just commands:

```bash
# Install Just (optional but recommended)
curl --proto '=https' --tlsv1.2 -sSf https://just.systems/install.sh | bash

# Build and start all services
just up

# Or without Just
docker compose -f docker-compose.local.yml up
```

Services will be available at:
- **Django app**: http://localhost:8000
- **API Documentation**: http://localhost:8000/api/docs/
- **Admin Interface**: http://localhost:8000/admin/
- **Mailpit** (email testing): http://localhost:8025
- **Flower** (Celery monitoring): http://localhost:5555

### Local Development Setup (Without Docker)

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd instarchiver-backend
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements/local.txt
   ```

4. Set up environment variables:
   ```bash
   cp .envs/.local/.django.example .envs/.local/.django
   cp .envs/.local/.postgres.example .envs/.local/.postgres
   # Edit the files with your configuration
   ```

5. Run migrations:
   ```bash
   python manage.py migrate
   ```

6. Create a superuser:
   ```bash
   python manage.py createsuperuser
   ```

7. Start the development server:
   ```bash
   python manage.py runserver
   ```

## API Endpoints

### Instagram API

- **List Users**: `GET /api/instagram/users/`
  - Supports search, filtering, and cursor pagination
  - Search fields: username, full_name, biography
  - Ordering: created_at, updated_at, username, full_name

- **User Detail**: `GET /api/instagram/users/<uuid>/`
  - Cached for 30 seconds for improved performance
  - Includes user stories and history status

- **Process Instagram Data**: `POST /api/instagram/inject-data/`
  - Endpoint for importing Instagram data

### API Documentation

Once the server is running, you can access:
- **Interactive API Docs**: http://localhost:8000/api/docs/
- **API Schema**: http://localhost:8000/api/schema/
- **Admin Interface**: http://localhost:8000/admin/

## Development Workflow

### Using Just Commands

The project includes a `justfile` for common tasks:

```bash
# List all available commands
just

# Build Docker images
just build

# Start containers
just up

# Stop containers
just down

# Remove containers and volumes
just prune

# View logs (optionally specify service)
just logs
just logs django

# Run Django management commands
just manage migrate
just manage createsuperuser
just manage shell

# Execute commands in Django container
just django python manage.py test
just django bash
```

### Testing & Quality

**Run tests with coverage**:
```bash
# With Docker
just django pytest --cov --cov-branch

# Without Docker
pytest --cov --cov-branch
coverage html
open htmlcov/index.html
```

**Code formatting and linting**:
```bash
# Format code
ruff format

# Check and fix linting issues
ruff check --fix

# Type checking
mypy core
```

**Pre-commit hooks**:
```bash
# Install pre-commit hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

### Background Tasks with Celery

Start a Celery worker:
```bash
celery -A config.celery_app worker -l info
```

Start Celery beat scheduler (for periodic tasks):
```bash
celery -A config.celery_app beat
```

Or combine worker and beat (development only):
```bash
celery -A config.celery_app worker -B -l info
```

Monitor tasks with Flower:
```bash
celery -A config.celery_app flower
```

## Docker Commands

### Manual Docker Compose Commands

If not using Just, you can use Docker Compose directly:

```bash
# Build and start all services
docker compose -f docker-compose.local.yml up --build

# Run in background
docker compose -f docker-compose.local.yml up -d

# View logs
docker compose -f docker-compose.local.yml logs -f django

# Run Django commands
docker compose -f docker-compose.local.yml run --rm django python manage.py migrate
docker compose -f docker-compose.local.yml run --rm django python manage.py createsuperuser

# Run tests
docker compose -f docker-compose.local.yml run --rm django pytest

# Stop services
docker compose -f docker-compose.local.yml down

# Remove volumes
docker compose -f docker-compose.local.yml down -v
```

## Configuration

### Environment Variables

The application uses environment-specific settings:
- **Development**: `.envs/.local/`
- **Production**: Environment variables or `.envs/.production/`

Key environment variables:
- `DJANGO_SECRET_KEY`: Secret key for Django
- `DJANGO_DEBUG`: Enable/disable debug mode
- `DATABASE_URL`: PostgreSQL connection string
- `REDIS_URL`: Redis connection string
- `SENTRY_DSN`: Sentry error tracking (production)

## Production Deployment

### Docker Production

Build and run with production configuration:

```bash
# Build production image
docker-compose -f docker-compose.production.yml build

# Start production services
docker-compose -f docker-compose.production.yml up -d

# Run migrations
docker-compose -f docker-compose.production.yml exec django python manage.py migrate

# Create superuser
docker-compose -f docker-compose.production.yml exec django python manage.py createsuperuser

# Collect static files
docker-compose -f docker-compose.production.yml exec django python manage.py collectstatic --noinput
```

### Manual Deployment

1. Set up PostgreSQL and Redis
2. Configure environment variables
3. Install dependencies: `pip install -r requirements/production.txt`
4. Run migrations: `python manage.py migrate`
5. Collect static files: `python manage.py collectstatic`
6. Start services with Gunicorn and Celery

### Deployment Checklist

- [ ] Set `DJANGO_DEBUG=False`
- [ ] Configure `DJANGO_ALLOWED_HOSTS`
- [ ] Set secure `DJANGO_SECRET_KEY`
- [ ] Configure database (`DATABASE_URL`)
- [ ] Configure Redis (`REDIS_URL`)
- [ ] Set up Sentry error tracking (`SENTRY_DSN`)
- [ ] Configure email backend
- [ ] Set up SSL/TLS certificates
- [ ] Configure static file serving
- [ ] Set up monitoring and logging

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
