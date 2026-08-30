"""Authenticated external identity resolved from a verified JWT."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Principal:
    subject: str
    email: str | None = None
    display_name: str | None = None
