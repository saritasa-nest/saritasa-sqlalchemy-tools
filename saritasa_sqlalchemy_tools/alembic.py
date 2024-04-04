import asyncio
import dataclasses
import importlib
import logging.config
import typing

import alembic
import alembic.config
import sqlalchemy
import sqlalchemy.ext.asyncio
import sqlalchemy.sql.schema


@dataclasses.dataclass
class AlembicMigrations:
    """Class for managing alembic migrations."""

    target_metadata: sqlalchemy.sql.schema.MetaData
    db_url: sqlalchemy.engine.URL | None = None
    db_driver: str = ""
    db_user: str = ""
    db_name: str = ""
    db_password: str = ""
    db_host: str = ""
    db_port: int = 0
    db_schema: str = ""
    query: dict[str, typing.Any] | None = None
    plugins: tuple[str, ...] = ()

    @property
    def alembic_config(self) -> alembic.config.Config:
        """Get alembic config."""
        return alembic.context.config

    @property
    def database_url(self) -> str | sqlalchemy.engine.URL:
        """Get database url."""
        if self.db_url:
            return self.db_url
        if database_url := self.alembic_config.get_main_option(
            "sqlalchemy.url",
        ):
            return database_url
        return sqlalchemy.engine.URL(
            drivername=self.db_driver,
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            query=self.query or {},  # type: ignore
        )

    @property
    def logger(self) -> logging.Logger:
        """Get logger."""
        return logging.getLogger("alembic")

    def setup_config(self) -> None:
        """Set up config."""
        if self.alembic_config.config_file_name is not None:
            logging.config.fileConfig(self.alembic_config.config_file_name)

    def import_plugins(self) -> None:
        """Import plugins."""
        self.logger.info("Set up plugins.")
        for plugin in self.plugins:
            self.logger.info(f"Importing plugin '{plugin}'.")
            importlib.import_module(plugin)

    def run_migrations_offline(self) -> None:
        """Run migrations in 'offline' mode.

        This configures the context with just a URL
        and not an Engine, though an Engine is acceptable
        here as well.  By skipping the Engine creation
        we don't even need a DBAPI to be available.

        Calls to context.execute() here emit the given string to the
        script output.

        """
        alembic.context.configure(
            url=self.database_url,
            target_metadata=self.target_metadata,
            literal_binds=True,
            dialect_opts={
                "paramstyle": "named",
            },
        )

        with alembic.context.begin_transaction():
            alembic.context.run_migrations()

    def set_up_schema(
        self,
        connection: sqlalchemy.engine.Connection,
    ) -> None:
        """Set up schema for migrations."""
        self.logger.info(f"Setting up schema '{self.db_schema}'.")
        connection.execute(
            sqlalchemy.text(f"create schema if not exists {self.db_schema}"),
        )
        # set search path on the connection, which ensures that
        # PostgreSQL will emit all CREATE / ALTER / DROP statements
        # in terms of this schema by default
        connection.execute(
            sqlalchemy.text(f"set search_path to {self.db_schema}"),
        )
        connection.commit()

        # make use of non-supported SQLAlchemy attribute to ensure
        # the dialect reflects tables in terms of the current schema name
        connection.dialect.default_schema_name = self.db_schema

    def do_run_migrations(
        self,
        connection: sqlalchemy.engine.Connection,
    ) -> None:
        """Apply migrations."""
        if self.db_schema:
            self.set_up_schema(connection=connection)
        alembic.context.configure(
            connection=connection,
            target_metadata=self.target_metadata,
        )
        with alembic.context.begin_transaction():
            alembic.context.run_migrations()

    async def run_async_migrations(self) -> None:
        """Run async migrations.

        In this scenario we need to create an Engine and associate a connection
        with the context.

        """
        connectable = sqlalchemy.ext.asyncio.async_engine_from_config(
            self.alembic_config.get_section(
                self.alembic_config.config_ini_section,
                {},
            ),
            prefix="sqlalchemy.",
            poolclass=sqlalchemy.pool.NullPool,
            url=self.database_url,
        )

        async with connectable.connect() as connection:
            await connection.run_sync(self.do_run_migrations)

        await connectable.dispose()

    def run_migrations_online(self) -> None:
        """Run migrations in 'online' mode."""
        asyncio.run(self.run_async_migrations())

    def run(self) -> None:
        """Run migrations."""
        self.setup_config()
        self.import_plugins()
        if alembic.context.is_offline_mode():
            self.run_migrations_offline()
        else:
            self.run_migrations_online()
