"""widen encrypted PII columns to TEXT

Fernet ciphertext is always longer than the plaintext it encrypts (version
byte + timestamp + IV + HMAC, all base64-encoded), so the VARCHAR(n) lengths
chosen for the plaintext were too small for the ciphertext actually stored
via EncryptedString. This widens the four affected patients columns to TEXT,
matching the corrected EncryptedString type (core/security.py), which now
declares `impl = Text` instead of `impl = String`.

Revision ID: 0002_encrypted_columns_to_text
Revises: 0001_initial
Create Date: 2026-08-14
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_encrypted_columns_to_text"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COLUMNS = ["national_code", "phone", "address", "emergency_contact"]


def upgrade() -> None:
    for column in _COLUMNS:
        op.alter_column(
            "patients",
            column,
            type_=sa.Text(),
            existing_type=sa.String(),
            existing_nullable=True,
        )


def downgrade() -> None:
    # Lengths restored to match the original 0001_initial definitions.
    # Note: if any ciphertext currently stored is longer than these limits,
    # this downgrade will fail (or truncate, depending on DB settings) —
    # that data loss is inherent to reverting the fix, not a migration bug.
    op.alter_column(
        "patients",
        "national_code",
        type_=sa.String(64),
        existing_type=sa.Text(),
        existing_nullable=False,
    )
    op.alter_column(
        "patients",
        "phone",
        type_=sa.String(64),
        existing_type=sa.Text(),
        existing_nullable=False,
    )
    op.alter_column(
        "patients",
        "address",
        type_=sa.String(512),
        existing_type=sa.Text(),
        existing_nullable=True,
    )
    op.alter_column(
        "patients",
        "emergency_contact",
        type_=sa.String(255),
        existing_type=sa.Text(),
        existing_nullable=True,
    )
