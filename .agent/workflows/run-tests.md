---
description: Run tests with coverage
---

# Running Tests with Coverage

This workflow runs the full test suite with coverage reporting.

## Steps

// turbo-all

1. **Run tests with coverage:**
   ```bash
   just django pytest --cov --cov-branch
   ```

2. **Generate HTML coverage report (optional):**
   ```bash
   just django coverage html
   ```

   The HTML report will be available in `htmlcov/index.html`

3. **Run specific test file:**
   ```bash
   just django pytest path/to/test_file.py --cov
   ```

4. **Run tests for specific app:**
   ```bash
   just django pytest instagram/tests/ --cov=instagram
   ```

## Coverage Targets

- Minimum 80% coverage for new code
- Coverage includes: `core/**`, `settings/**`, `api_logs/**`, `instagram/**`, `authentication/**`
- Excludes: `*/migrations/*`, `*/tests/*`

## Notes

- Tests use `config.settings.test` configuration
- Database is reused between test runs for speed (`--reuse-db`)
- All tests run inside Docker containers
