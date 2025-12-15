---
description: Check and fix code quality
---

# Code Quality Checks

This workflow runs linting, formatting, and type checking on the codebase.

## Steps

// turbo-all

1. **Format code with Ruff:**
   ```bash
   just django ruff format
   ```

2. **Check and auto-fix linting issues:**
   ```bash
   just django ruff check --fix
   ```

3. **Type checking with MyPy:**
   ```bash
   just django mypy core
   ```

4. **Run all pre-commit hooks:**
   ```bash
   just django pre-commit run --all-files
   ```

## What Gets Checked

### Ruff Linting
- Python 3.12+ modern syntax
- Django best practices
- Security issues
- Code complexity
- Import organization (force-single-line)
- Type annotations (future)

### MyPy Type Checking
- Type hints validation
- Django plugin for model types
- DRF plugin for serializer types

### Pre-commit Hooks
- Trailing whitespace
- End of file fixes
- YAML/JSON validation
- Ruff formatting and linting
- Django upgrade checks

## Configuration

- Ruff config: `pyproject.toml` (lines 66-148)
- MyPy config: `pyproject.toml` (lines 26-45)
- Pre-commit: `.pre-commit-config.yaml`

## Notes

- All commands run inside Docker containers
- Ruff uses force-single-line imports
- Some rules are ignored (see pyproject.toml)
