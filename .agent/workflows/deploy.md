---
description: Deploy to production
---

# Production Deployment

This workflow guides you through deploying the application to production.

## Pre-deployment Checklist

Before deploying, ensure all these items are completed:

- [ ] All tests pass: `just django pytest --cov`
- [ ] Code quality checks pass: `just django ruff check`
- [ ] Type checking passes: `just django mypy core`
- [ ] Migrations tested on staging environment
- [ ] Environment variables configured
- [ ] Database backup created
- [ ] Rollback plan prepared
- [ ] Monitoring and alerting configured

## Environment Configuration

### Required Environment Variables

1. **Set production environment variables:**
   ```bash
   DJANGO_DEBUG=False
   DJANGO_ALLOWED_HOSTS=your-domain.com,www.your-domain.com
   DJANGO_SECRET_KEY=<secure-random-key>
   DATABASE_URL=postgres://user:password@host:port/dbname
   REDIS_URL=redis://host:port/0
   SENTRY_DSN=<your-sentry-dsn>
   ```

2. **Verify environment file:**
   - Check `.envs/.production/.django`
   - Check `.envs/.production/.postgres`
   - Ensure no sensitive data in version control

## Deployment Steps

### 1. Build Production Image

```bash
docker-compose -f docker-compose.production.yml build
```

### 2. Start Production Services

```bash
docker-compose -f docker-compose.production.yml up -d
```

This starts:
- Django app with Gunicorn
- PostgreSQL database
- Redis cache
- Celery worker
- Celery beat scheduler

### 3. Run Database Migrations

```bash
docker-compose -f docker-compose.production.yml exec django python manage.py migrate
```

### 4. Collect Static Files

```bash
docker-compose -f docker-compose.production.yml exec django python manage.py collectstatic --noinput
```

### 5. Create Superuser (First Deployment Only)

```bash
docker-compose -f docker-compose.production.yml exec django python manage.py createsuperuser
```

### 6. Verify Deployment

1. **Check service health:**
   ```bash
   docker-compose -f docker-compose.production.yml ps
   ```

2. **Check application logs:**
   ```bash
   docker-compose -f docker-compose.production.yml logs -f django
   ```

3. **Test API endpoints:**
   - Visit: `https://your-domain.com/health/`
   - Visit: `https://your-domain.com/api/docs/`
   - Test authentication endpoints
   - Test critical API endpoints

4. **Verify Celery workers:**
   ```bash
   docker-compose -f docker-compose.production.yml logs -f celeryworker
   ```

5. **Check database connectivity:**
   ```bash
   docker-compose -f docker-compose.production.yml exec django python manage.py dbshell
   ```

## Post-deployment Tasks

### 1. Configure Database Settings

Access Django admin and configure:
- CoreAPISetting (external API credentials)
- FirebaseAdminSetting (Firebase service account)
- OpenAISetting (if using OpenAI)

### 2. Set Up SSL/TLS

- Configure SSL certificates (Let's Encrypt recommended)
- Update NGINX/reverse proxy configuration
- Verify HTTPS redirects

### 3. Configure Monitoring

- Verify Sentry error tracking
- Set up uptime monitoring
- Configure log aggregation
- Set up performance monitoring

### 4. Set Up Backups

- Configure automated database backups
- Test backup restoration process
- Set up media file backups
- Document backup retention policy

## Rollback Procedure

If deployment fails:

1. **Stop new containers:**
   ```bash
   docker-compose -f docker-compose.production.yml down
   ```

2. **Restore previous image:**
   ```bash
   docker-compose -f docker-compose.production.yml up -d
   ```

3. **Rollback migrations if needed:**
   ```bash
   docker-compose -f docker-compose.production.yml exec django python manage.py migrate app_name previous_migration
   ```

4. **Restore database from backup if needed:**
   ```bash
   # Follow your backup restoration procedure
   ```

## Monitoring Commands

### View Logs

```bash
# All services
docker-compose -f docker-compose.production.yml logs -f

# Specific service
docker-compose -f docker-compose.production.yml logs -f django
docker-compose -f docker-compose.production.yml logs -f celeryworker
```

### Check Service Status

```bash
docker-compose -f docker-compose.production.yml ps
```

### Restart Services

```bash
# Restart all
docker-compose -f docker-compose.production.yml restart

# Restart specific service
docker-compose -f docker-compose.production.yml restart django
```

### Execute Management Commands

```bash
docker-compose -f docker-compose.production.yml exec django python manage.py <command>
```

## Security Checklist

- [ ] `DEBUG=False` in production
- [ ] Strong `SECRET_KEY` configured
- [ ] `ALLOWED_HOSTS` properly configured
- [ ] HTTPS/SSL enabled
- [ ] CSRF protection enabled (default)
- [ ] Secure cookies configured
- [ ] Database credentials secured
- [ ] API keys in database settings, not code
- [ ] Sentry DSN configured
- [ ] Rate limiting configured
- [ ] CORS settings reviewed
- [ ] File upload limits configured

## Performance Optimization

- [ ] Redis caching enabled
- [ ] Database indexes added
- [ ] Static files served via CDN
- [ ] Gunicorn workers configured appropriately
- [ ] Celery workers scaled appropriately
- [ ] Database connection pooling configured
- [ ] Query optimization reviewed

## Troubleshooting

### Application won't start
- Check environment variables
- Review logs: `docker-compose -f docker-compose.production.yml logs django`
- Verify database connectivity
- Check Redis connectivity

### Migrations fail
- Review migration SQL
- Check database permissions
- Verify database backup exists
- Consider running migrations manually

### Static files not loading
- Verify `collectstatic` ran successfully
- Check NGINX/reverse proxy configuration
- Verify `STATIC_ROOT` and `STATIC_URL` settings

### Celery tasks not running
- Check Celery worker logs
- Verify Redis connectivity
- Check task queue status
- Review Celery configuration

## Notes

- Always test on staging before production
- Keep deployment documentation updated
- Document any manual steps required
- Maintain rollback procedures
- Monitor application after deployment
