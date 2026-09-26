"""Tiny additive schema migrator for the SQLite dev database.

`db.create_all()` creates missing TABLES but never adds missing COLUMNS, so an
existing instance/boardroom.db from an earlier version of the app would break
with "no such column" the moment a new field is read. This walks the declared
models, compares them with PRAGMA table_info, and ALTERs in anything missing.

It only ever ADDs columns — it never drops or rewrites data.
"""
import logging

from sqlalchemy import inspect, text

from database import db

logger = logging.getLogger("boardroom.migrations")

_SQLITE_TYPES = {
    "INTEGER": "INTEGER", "VARCHAR": "VARCHAR", "TEXT": "TEXT",
    "FLOAT": "FLOAT", "DATETIME": "DATETIME", "BOOLEAN": "BOOLEAN",
}


def _column_sql_type(column):
    try:
        return column.type.compile(dialect=db.engine.dialect)
    except Exception:
        return "TEXT"


def ensure_schema(app):
    """Adds any model column that is missing from the live SQLite database."""
    with app.app_context():
        db.create_all()

        inspector = inspect(db.engine)
        existing_tables = set(inspector.get_table_names())
        added = []

        for mapper in db.Model.registry.mappers:
            table = mapper.local_table
            if table is None or table.name not in existing_tables:
                continue

            live_columns = {c["name"] for c in inspector.get_columns(table.name)}
            for column in table.columns:
                if column.name in live_columns:
                    continue

                col_type = _column_sql_type(column)
                default_clause = ""
                default = getattr(column, "default", None)
                if default is not None and getattr(default, "is_scalar", False):
                    value = default.arg
                    if isinstance(value, str):
                        default_clause = f" DEFAULT '{value}'"
                    elif isinstance(value, (int, float)):
                        default_clause = f" DEFAULT {value}"

                sql = f'ALTER TABLE "{table.name}" ADD COLUMN "{column.name}" {col_type}{default_clause}'
                try:
                    with db.engine.begin() as conn:
                        conn.execute(text(sql))
                    added.append(f"{table.name}.{column.name}")
                except Exception as e:  # pragma: no cover - defensive
                    logger.warning("Could not add column %s.%s: %s", table.name, column.name, e)

        if added:
            logger.info("Schema migration added %d column(s): %s", len(added), ", ".join(added))
        return added
