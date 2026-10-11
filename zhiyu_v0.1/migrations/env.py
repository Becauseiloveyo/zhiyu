import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool
from sqlalchemy.engine import Connection

from zhiyu.db import infrastructure, models  # noqa: F401
from zhiyu.db.base import Base

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
target_metadata = Base.metadata


def migrate(connection: Connection) -> None:
    context.configure(
        connection=connection, target_metadata=target_metadata, compare_type=True, compare_server_default=True
    )
    with context.begin_transaction():
        context.run_migrations()


def run() -> None:
    url = os.environ.get("ZHIYU_DATABASE_URL", config.get_main_option("sqlalchemy.url"))
    if context.is_offline_mode():
        context.configure(
            url=url, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"}
        )
        with context.begin_transaction():
            context.run_migrations()
    elif config.attributes.get("connection") is not None:
        migrate(config.attributes["connection"])
    else:
        engine = create_engine(
            url, poolclass=pool.NullPool, hide_parameters=True, connect_args={"connect_timeout": 5}
        )
        try:
            with engine.connect() as connection:
                migrate(connection)
        finally:
            engine.dispose()


run()
