"""Limits shared by the schemas, the models and the AI module.

The frontend mirrors the user-facing ones in frontend/lib/constants.ts; the
API is the source of truth and validates on every request.

The Alembic migration keeps its own literal column sizes on purpose: a
migration is a snapshot of the schema, so changing a column size here needs a
new revision.
"""

# --- Users -------------------------------------------------------------------
EMAIL_MAX_LENGTH = 320  # column size: 64 (local part) + "@" + 255 (domain)
PASSWORD_MIN_LENGTH = 8
PASSWORD_MAX_LENGTH = 128  # caps the work argon2 does on attacker-supplied input
PASSWORD_HASH_MAX_LENGTH = 255  # column size; an argon2id hash is about 100 characters

# --- Notes -------------------------------------------------------------------
TITLE_MAX_LENGTH = 200  # column size
# Also the AI input limit, so every accepted note is summarized in full.
CONTENT_MAX_LENGTH = 20_000
TAG_MAX_LENGTH = 50  # the ?tag= filter value
