"""Shared database model metadata boundary."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, JSON, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, mapped_column

JSONColumn = JSON().with_variant(JSONB(), "postgresql")


def new_id() -> str:
    """Generate a stable identifier for a database row."""
    return str(uuid.uuid4())


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """Declarative base for all database models."""


def id_column():
    """Primary key column using a stable generated identifier."""
    return mapped_column(String(36), primary_key=True, default=new_id)


def created_at_column():
    return mapped_column(DateTime(timezone=True), default=utc_now, nullable=False)
