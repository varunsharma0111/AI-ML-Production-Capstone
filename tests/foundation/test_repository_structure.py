"""Phase 1 checks for the intentionally code-free repository foundation."""

from __future__ import annotations

import tomllib
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_required_foundation_files_exist() -> None:
    required_paths = (
        ".editorconfig",
        ".gitattributes",
        ".gitignore",
        ".pre-commit-config.yaml",
        "CONTRIBUTING.md",
        "README.md",
        "pyproject.toml",
        ".github/workflows/ci.yml",
        "docs/development/local-development.md",
        "docs/implementation-plan.md",
        "docs/progress.md",
    )

    missing_paths = [path for path in required_paths if not (REPOSITORY_ROOT / path).is_file()]

    assert not missing_paths, f"Missing Phase 1 foundation files: {', '.join(missing_paths)}"


def test_planned_top_level_directories_exist() -> None:
    required_directories = (
        "apps",
        "config",
        "data",
        "database",
        "docs",
        "infra",
        "ml",
        "services",
        "tests",
    )

    missing_directories = [
        directory
        for directory in required_directories
        if not (REPOSITORY_ROOT / directory).is_dir()
    ]

    assert not missing_directories, (
        f"Missing planned top-level directories: {', '.join(missing_directories)}"
    )


def test_python_quality_configuration_is_parseable() -> None:
    with (REPOSITORY_ROOT / "pyproject.toml").open("rb") as config_file:
        configuration = tomllib.load(config_file)

    assert {"ruff", "mypy", "pytest"}.issubset(configuration["tool"])
