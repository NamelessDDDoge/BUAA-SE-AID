# BUAA-SE-AID Test System

The repository keeps tests close to each subsystem, with repository-root tests reserved for cross-system contracts, E2E, smoke, and shared helpers.

## Unified Entry

Run the default local test gate from the repository root:

```powershell
.\scripts\test_all.ps1
```

Default behavior:

- Runs backend migrations and backend tests in the `detect` conda environment.
- Runs ai-service and ai-training pytest suites in the `detect` conda environment.
- Runs frontend-user and frontend-admin Vitest suites.
- Excludes tests marked `gpu`, `e2e`, or `slow`.
- Stops at the first failing command and returns a non-zero exit code.

Useful variants:

```powershell
.\scripts\test_all.ps1 -Suite backend
.\scripts\test_all.ps1 -Suite python
.\scripts\test_all.ps1 -Suite frontend
.\scripts\test_all.ps1 -Suite all -IncludeGPU -IncludeE2E
.\scripts\test_all.ps1 -SkipFrontend
.\scripts\test_all.ps1 -CondaEnv detect
.\scripts\test_all.ps1 -DatabaseMode local
```

Windows note: the runner sets `PYTHONIOENCODING=utf-8`, `PYTHONUTF8=1`, and `DATABASE_MODE=local` before invoking pytest to avoid GBK output failures and remote SSH database timeouts during local verification.

## Direct Subsystem Commands

Backend:

```powershell
cd AIDetector/code/backend/backend-code
conda run --no-capture-output -n detect python manage.py migrate
conda run --no-capture-output -n detect pytest core/tests -m "not gpu and not e2e and not slow" -q
```

AI service:

```powershell
cd AIDetector/code/ai-service/ai-service-code
conda run --no-capture-output -n detect pytest tests -m "not gpu and not e2e and not slow" -q
```

AI training:

```powershell
cd AIDetector/code/ai-training/ai-training-code
conda run --no-capture-output -n detect pytest tests -m "not gpu and not e2e and not slow" -q
```

Frontend:

```powershell
cd AIDetector/code/frontend/frontend-user
npm test

cd ../frontend-admin
npm test
```

## Adding New Tests

1. Put pure function and small class tests under `unit/`.
2. Put Django ORM/APIClient/file-system tests under `integration/`.
3. Put multi-service browser or service-chain tests under repository-root `tests/e2e/`.
4. Keep large fixtures out of git; small deterministic fixtures belong under each subsystem's `fixtures/` directory.
5. Update `tests/docs/test_matrix.md` when a test maps to a design-document unit.
