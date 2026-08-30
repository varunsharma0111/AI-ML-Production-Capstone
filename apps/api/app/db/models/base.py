"""Declarative base and common database types."""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all PostgreSQL ORM models."""
