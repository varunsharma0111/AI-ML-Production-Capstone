# Contributing

## Scope and workflow

Keep changes small, reviewable, and aligned with the approved implementation phase. Do not add secrets, generated artifacts, or environment-specific configuration to Git. Use conventional commit prefixes such as `docs:`, `ci:`, `test:`, `feat:`, or `fix:`.

Create a focused branch, make one concern clear in the pull request, and explain the validation performed. Changes that alter architecture must update the relevant architecture document or ADR.

## Local quality checks

Phase 1 has Python quality tooling because it includes a repository-structure test. This does not install or implement the application.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install ruff==0.12.11 mypy==1.18.2 pytest==8.4.2 pre-commit==4.3.0
ruff format --check .
ruff check .
mypy tests
pytest
pre-commit run --all-files
```

To install the optional commit hook after the checks are available:

```powershell
pre-commit install
```

React/TypeScript tooling and application dependencies are intentionally deferred to Phase 3. Docker Compose is deferred to the production-delivery phase; see [local development](docs/development/local-development.md).

## Pull request checklist

- [ ] The change remains within the approved phase.
- [ ] No secret, token, dataset, model artifact, or generated output is committed.
- [ ] Relevant formatting, linting, type, and test checks pass.
- [ ] Documentation and architecture decisions are updated when behavior or scope changes.
