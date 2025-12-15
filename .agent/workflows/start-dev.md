---
description: Start development environment
---

# Start Development Environment

This workflow starts the complete development environment with all services.

## Steps

// turbo-all

1. **Start all services:**
   ```bash
   just up
   ```

   This starts:
   - Django app (http://localhost:8000)
   - PostgreSQL database
   - Redis cache
   - Celery worker
   - Celery beat scheduler
   - Flower (Celery monitoring at http://localhost:5555)
   - Mailpit (email testing at http://localhost:8025)

2. **Build containers (if needed):**
   ```bash
   just build
   ```

3. **View logs:**
   ```bash
   just logs
   ```

   Or for specific service:
   ```bash
   just logs django
   ```

4. **Stop all services:**
   ```bash
   just down
   ```

5. **Remove containers and volumes:**
   ```bash
   just prune
   ```

## Available Services

Once running, access:
- **Django app**: http://localhost:8000
- **API Documentation**: http://localhost:8000/api/docs/
- **Admin Interface**: http://localhost:8000/admin/
- **Mailpit** (email testing): http://localhost:8025
- **Flower** (Celery monitoring): http://localhost:5555

## First Time Setup

If this is your first time running the project:

1. **Create superuser:**
   ```bash
   just manage createsuperuser
   ```

2. **Configure database settings:**
   - Visit http://localhost:8000/admin/
   - Configure CoreAPISetting
   - Configure FirebaseAdminSetting (if needed)

## Common Commands

### Django Management

```bash
# Run migrations
just manage migrate

# Create migrations
just manage makemigrations

# Django shell
just manage shell

# Run custom command
just django python manage.py <command>
```

### Database

```bash
# Access database shell
just manage dbshell

# Reset database (WARNING: deletes all data)
just down
just prune
just up
just manage migrate
```

### Celery

```bash
# View Celery worker logs
just logs celeryworker

# View Celery beat logs
just logs celerybeat

# Monitor tasks in Flower
# Visit: http://localhost:5555
```

## Troubleshooting

### Port already in use
If port 8000 is already in use:
```bash
# Find and kill process using port 8000
lsof -ti:8000 | xargs kill -9
```

### Database connection issues
```bash
# Restart PostgreSQL container
docker-compose -f docker-compose.local.yml restart postgres
```

### Containers won't start
```bash
# Remove all containers and volumes, then rebuild
just prune
just build
just up
```

### Changes not reflecting
```bash
# Rebuild containers
just build
just up
```

## Notes

- All commands run inside Docker containers
- Database data persists in Docker volumes
- Redis cache is cleared on restart
- Mailpit captures all outgoing emails in development
