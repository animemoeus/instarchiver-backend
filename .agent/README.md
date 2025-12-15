# Antigravity Configuration Summary

This document provides an overview of the Antigravity configuration created for the **instarchiver-backend** project.

## What Was Created

### 1. Main Rules: `.agent/rules/`

A comprehensive rules folder containing project guidelines covering:

- **Development Environment**: Docker-first development with justfile commands
- **Code Quality Standards**: Ruff linting, formatting, and MyPy type checking
- **Architecture Patterns**: Django settings, models, admin, API development
- **External API Integration**: Core API client usage
- **Background Tasks**: Celery task patterns
- **File Organization**: App structure and import organization
- **Database Migrations**: Best practices and workflows
- **Security Considerations**: Sensitive data handling
- **Common Workflows**: Step-by-step guides for common tasks
- **Performance Optimization**: Caching, database, and task optimization
- **Error Handling**: Logging and exception handling
- **Deployment**: Production deployment checklist

### 2. Workflow Files: `.agent/workflows/`

Five workflow files for common development tasks:

#### `/start-dev` - Start Development Environment
- Starts all Docker services (Django, PostgreSQL, Redis, Celery, Flower, Mailpit)
- First-time setup instructions
- Common management commands
- Troubleshooting guide

#### `/run-tests` - Run Tests with Coverage
- Full test suite with coverage reporting
- Specific test file execution
- HTML coverage report generation
- Coverage targets and configuration

#### `/code-quality` - Check and Fix Code Quality
- Ruff formatting and linting
- MyPy type checking
- Pre-commit hooks
- Configuration references

#### `/migrations` - Create and Apply Database Migrations
- Creating migrations (all apps or specific app)
- Reviewing migrations before applying
- Applying and rolling back migrations
- Best practices and common issues
- Production migration checklist

#### `/deploy` - Deploy to Production
- Pre-deployment checklist
- Environment configuration
- Step-by-step deployment process
- Post-deployment tasks
- Rollback procedures
- Monitoring and troubleshooting

## How to Use

### Automatic Rules

Antigravity will automatically read and follow the rules in `.agent/rules/` when working with your codebase. No action needed! The rules ensure:

- All commands run inside Docker containers
- Code quality standards are maintained
- Architecture patterns are followed
- Security best practices are enforced

### Using Workflows

Invoke workflows using slash commands:

```
/start-dev    - Start the development environment
/run-tests    - Run tests with coverage
/code-quality - Check and fix code quality
/migrations   - Create and apply database migrations
/deploy       - Deploy to production
```

Workflows marked with `// turbo-all` will auto-run all commands without asking for permission.

## Key Features

### Docker-First Development

All development happens inside Docker containers. The rules enforce this pattern and prevent suggestions to run commands directly on the host machine.

### Database-Backed Configuration

The project uses database models for runtime configuration (API keys, Firebase credentials) instead of environment variables. The rules guide Antigravity to use this pattern correctly.

### Code Quality Automation

Workflows include automatic formatting, linting, and type checking with Ruff and MyPy, following the project's strict code quality standards.

### Comprehensive Testing

Test workflows include coverage reporting with specific targets (80% minimum for new code) and proper test execution inside Docker.

### Production-Ready Deployment

The deployment workflow includes a complete checklist, step-by-step instructions, rollback procedures, and post-deployment verification.

## Project-Specific Patterns

### Two User Models

The project has two separate User models:
1. `core.users.models.User` - Django authentication
2. `instagram.models.User` - Instagram profile data

The rules help Antigravity understand when to use each model.

### Admin Organization

Admin files are split into separate files in `app/admin/` directory using the Unfold admin theme. The rules provide templates for creating new admin classes.

### External API Integration

All external API calls use the centralized Core API client with automatic request logging. The rules enforce this pattern.

### Background Tasks

Celery tasks follow specific patterns with retry logic, logging, and proper error handling. The rules provide templates for creating new tasks.

## Benefits

1. **Consistency**: Ensures all code follows the same patterns and standards
2. **Efficiency**: Workflows automate common tasks with turbo mode
3. **Safety**: Enforces Docker usage and prevents direct host commands
4. **Quality**: Automatic code quality checks and testing
5. **Documentation**: Self-documenting workflows for common operations
6. **Onboarding**: New team members can quickly understand project patterns

## Customization

You can customize the configuration by:

1. **Editing `.agent/rules/`**: Add project-specific rules or modify existing ones in the rules folder
2. **Adding workflows**: Create new `.md` files in `.agent/workflows/`
3. **Updating workflow commands**: Modify existing workflows to match your needs

## Next Steps

1. Review the rules and workflows to ensure they match your project needs
2. Customize any patterns or commands that differ from your setup
3. Add any additional project-specific rules or workflows
4. Share the configuration with your team

## Support

If you need to modify the configuration:
- Rules folder: `.agent/rules/`
- Workflows: `.agent/workflows/*.md`
- Workflow format: YAML frontmatter + markdown content

For more information about Antigravity configuration, refer to the Antigravity documentation.
