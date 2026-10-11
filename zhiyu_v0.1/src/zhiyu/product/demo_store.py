"""Explicit versioned migration for isolated product metadata, outside the frozen core schema."""

import hashlib
import re

from sqlalchemy import inspect, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import Engine
from sqlalchemy.schema import CreateIndex, CreateSchema, CreateTable

from zhiyu.db.demo_control import ProductBase

REVISION = "zhiyu-product-demo/0001"


def ddl() -> str:
    dialect = postgresql.dialect()
    statements = [
        str(CreateTable(table).compile(dialect=dialect)).strip() + ";"
        for table in ProductBase.metadata.sorted_tables
    ]
    statements += [
        str(CreateIndex(index).compile(dialect=dialect)) + ";"
        for table in ProductBase.metadata.sorted_tables
        for index in sorted(table.indexes, key=lambda i: str(i.name))
    ]
    return "\n\n".join(statements) + "\n"


def initialize(engine: Engine, schema: str = "zhiyu_product") -> None:
    if not re.fullmatch(r"(?:zhiyu_product|test_demo_[a-f0-9]{32})", schema):
        raise ValueError("dedicated_product_schema_required")
    owner = REVISION + ":" + hashlib.sha256(ddl().encode()).hexdigest()
    with engine.begin() as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": schema})
        current = connection.execute(
            text("SELECT obj_description(oid, 'pg_namespace') FROM pg_namespace WHERE nspname=:name"),
            {"name": schema},
        ).first()
        if current is not None:
            if current[0] != owner or set(inspect(connection).get_table_names(schema=schema)) != {
                "demo_runs",
                "demo_run_steps",
            }:
                raise RuntimeError("product_schema_not_owned_or_migration_mismatch")
            return
        connection.execute(CreateSchema(schema))
        translated = connection.execution_options(schema_translate_map={"zhiyu_product": schema})
        ProductBase.metadata.create_all(translated)
        # Both strings are program constants or constrained identifiers, never browser input.
        connection.execute(text(f"COMMENT ON SCHEMA \"{schema}\" IS '{owner}'"))
