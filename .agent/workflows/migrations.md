---
description: Create and apply database migrations
---

# Database Migrations

This workflow handles creating and applying Django database migrations.

## Steps

### Creating Migrations

// turbo
1. **Generate migrations for all apps:**
   ```bash
   just manage makemigrations
   ```

2. **Generate migrations for specific app:**
   ```bash
   just manage makemigrations app_name
   ```

3. **Create empty migration (for data migrations):**
   ```bash
   just manage makemigrations --empty app_name
   ```

### Reviewing Migrations

4. **Check migration file before applying:**
   - Review the generated file in `app_name/migrations/`
   - Check for:
     - Data migrations that might timeout on large tables
     - Indexes on large tables (consider adding separately)
     - Non-nullable fields without defaults
     - Removing fields (should be separate from adding)

5. **Show migration SQL (without applying):**
   ```bash
   just manage sqlmigrate app_name migration_number
   ```

### Applying Migrations

// turbo
6. **Apply all pending migrations:**
   ```bash
   just manage migrate
   ```

7. **Apply migrations for specific app:**
   ```bash
   just manage migrate app_name
   ```

8. **Apply up to specific migration:**
   ```bash
   just manage migrate app_name migration_number
   ```

### Checking Migration Status

// turbo
9. **Show all migrations and their status:**
   ```bash
   just manage showmigrations
   ```

10. **Show migrations for specific app:**
    ```bash
    just manage showmigrations app_name
    ```

### Rolling Back Migrations

11. **Rollback to previous migration:**
    ```bash
    just manage migrate app_name previous_migration_number
    ```

12. **Rollback all migrations for an app:**
    ```bash
    just manage migrate app_name zero
    ```

## Best Practices

### Before Creating Migrations
- Ensure models are properly defined
- Add `db_index=True` for frequently queried fields
- Use appropriate field types
- Consider data migration needs

### Migration Review Checklist
- [ ] Migration file is properly named
- [ ] No sensitive data in migration
- [ ] Indexes won't timeout on large tables
- [ ] Non-nullable fields have defaults or data migration
- [ ] Backward compatibility considered
- [ ] Data migrations are idempotent

### Before Applying in Production
- [ ] Test migrations on staging environment
- [ ] Backup database
- [ ] Check migration SQL output
- [ ] Estimate migration time for large tables
- [ ] Plan for rollback if needed
- [ ] Schedule during maintenance window if needed

## Common Issues

### Non-nullable field without default
```python
# Add default or make nullable
field_name = models.CharField(max_length=100, default='')
# or
field_name = models.CharField(max_length=100, null=True, blank=True)
```

### Renaming fields
```python
# Use migrations.RenameField instead of remove + add
migrations.RenameField(
    model_name='mymodel',
    old_name='old_field',
    new_name='new_field',
)
```

### Data migrations
```python
# Create empty migration first
# Then add RunPython operation
from django.db import migrations

def forwards_func(apps, schema_editor):
    MyModel = apps.get_model('app_name', 'MyModel')
    # Data migration logic

def reverse_func(apps, schema_editor):
    # Rollback logic
    pass

class Migration(migrations.Migration):
    operations = [
        migrations.RunPython(forwards_func, reverse_func),
    ]
```

## Notes

- All migration commands run inside Docker containers
- Migrations are auto-discovered from all installed apps
- Test settings use separate test database
- Production migrations should be tested on staging first
