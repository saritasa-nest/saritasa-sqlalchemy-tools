import collections.abc
import pathlib

import pytest

import sqlalchemy
import sqlalchemy.ext.asyncio


def pytest_addoption(parser: pytest.Parser) -> None:
    """Set up cmd args."""
    parser.addoption(
        "--sqlalchemy-echo",
        action="store_true",
        default=False,
        help="Should sqlalchemy print sql queries",
    )
    parser.addini(
        "sqlalchemy_database_driver",
        "Driver for sqlalchemy.",
    )
    parser.addini(
        "sqlalchemy_username",
        "Username for sqlalchemy.",
    )
    parser.addini(
        "sqlalchemy_password",
        "Password for sqlalchemy.",
    )
    parser.addini(
        "sqlalchemy_host",
        "Host for sqlalchemy.",
    )
    parser.addini(
        "sqlalchemy_port",
        "Port for sqlalchemy.",
    )
    parser.addini(
        "sqlalchemy_database",
        "Name for database for sqlalchemy.",
    )
    parser.addini(
        "alembic_config",
        "Path to alembic config.",
    )


@pytest.fixture(scope="session")
def sqlalchemy_echo(request: pytest.FixtureRequest) -> bool:
    """Get `--sqlalchemy-echo` option."""
    return bool(request.config.getoption("--sqlalchemy-echo"))


@pytest.fixture(scope="session")
def database_url(request: pytest.FixtureRequest) -> str:
    """Override database url.

    Grab configs from settings and add support for pytest-xdist

    """
    worker_input = getattr(
        request.config,
        "workerinput",
        {
            "workerid": "",
        },
    )
    driver = str(
        request.config.inicfg.get("sqlalchemy_database_driver", ""),
    )
    if not driver:
        pytest.fail(
            reason="No driver for database is specified",
        )  # pragma: no cover
    username = str(request.config.inicfg.get("sqlalchemy_username", ""))
    if not username:
        pytest.fail(
            reason="No username for database is specified",
        )  # pragma: no cover
    password = str(request.config.inicfg.get("sqlalchemy_password", ""))
    if not password:
        pytest.fail(
            reason="No password for database is specified",
        )  # pragma: no cover
    host = str(request.config.inicfg.get("sqlalchemy_host", ""))
    if not host:
        pytest.fail(
            reason="No host for database is specified",
        )  # pragma: no cover
    port = int(str(request.config.inicfg.get("sqlalchemy_port", 5432)))
    database = str(
        request.config.inicfg.get(
            "sqlalchemy_database",
            "saritasa-sqlalchemy-tools",
        ),
    )
    return sqlalchemy.engine.URL(
        drivername=driver,
        username=username,
        password=password,
        host=host,
        port=port,
        database="-".join(
            filter(
                None,
                (
                    database,
                    worker_input["workerid"],
                ),
            ),
        ),
        query={},  # type: ignore
    )


@pytest.fixture(scope="session")
async def database(
    database_url: sqlalchemy.engine.URL,
) -> collections.abc.AsyncIterator[sqlalchemy.engine.URL]:
    """Create database for test."""
    await create_database(database_url)
    try:
        yield database_url
    finally:
        await drop_database(database_url)


@pytest.fixture(scope="session")
def alembic_database_setup(
    request: pytest.FixtureRequest,
    database_url: sqlalchemy.engine.URL,
) -> bool:
    """Set up database via alembic."""
    alembic_config_path = str(
        request.config.inicfg.get("alembic_config", "alembic.ini"),
    )
    if not pathlib.Path(alembic_config_path).exists():
        return False  # pragma: no cover
    import alembic.command
    import alembic.config

    alembic_cfg = alembic.config.Config(
        str(request.config.inicfg.get("alembic_config", "alembic.ini")),
    )
    alembic_cfg.set_main_option(
        "sqlalchemy.url",
        database_url.render_as_string(hide_password=False),
    )
    alembic.command.upgrade(alembic_cfg, "head")
    return True


@pytest.fixture(scope="session")
def manual_database_setup() -> collections.abc.Callable[..., None] | None:
    """Return logic which will set up database."""
    return None  # pragma: no cover


@pytest.fixture(scope="session")
async def sqlalchemy_engine(
    database: sqlalchemy.engine.URL,
    sqlalchemy_echo: bool,
    alembic_database_setup: bool,
    manual_database_setup: collections.abc.Callable[..., None] | None,
) -> collections.abc.AsyncIterator[sqlalchemy.ext.asyncio.AsyncEngine]:
    """Set up engine for test session."""
    if not alembic_database_setup and not manual_database_setup:
        pytest.fail(  # pragma: no cover
            reason=(
                "Couldn't locate alembic config and"
                "`manual_database_setup` is not redefined"
            ),
        )
    engine = sqlalchemy.ext.asyncio.create_async_engine(
        database,
        echo=sqlalchemy_echo,
    )
    try:
        if manual_database_setup:
            async with engine.begin() as connection:
                await connection.run_sync(manual_database_setup)
        yield engine
    finally:
        await engine.dispose()


@pytest.fixture
async def db_session(
    sqlalchemy_engine: sqlalchemy.ext.asyncio.AsyncEngine,
) -> collections.abc.AsyncIterator[sqlalchemy.ext.asyncio.AsyncSession]:
    """Set up db session for test.

    Start transaction and roll it back once test is completed.

    """
    connection = await sqlalchemy_engine.connect()
    trans = await connection.begin()

    session_maker = sqlalchemy.ext.asyncio.async_sessionmaker(
        bind=connection,
        expire_on_commit=False,
    )
    async with session_maker() as session:
        try:
            yield session
        finally:
            await session.close()
            await trans.rollback()
            await connection.close()


async def create_database(url: sqlalchemy.engine.URL) -> None:
    """Create database for tests."""
    database_name = url.database
    dbms_url = url.set(database="postgres")
    engine = sqlalchemy.ext.asyncio.create_async_engine(
        dbms_url,
        # Needed to avoid error
        # CREATE DATABASE cannot run inside a transaction block
        isolation_level="AUTOCOMMIT",
    )

    async with engine.connect() as connection:
        c = await connection.execute(
            sqlalchemy.text(
                f"SELECT 1 FROM pg_database WHERE datname='{database_name}'",  # noqa: S608
            ),
        )
        database_exists = c.scalar() == 1

    if database_exists:
        await drop_database(url)  # pragma: no cover

    async with engine.connect() as connection:
        await connection.execute(
            sqlalchemy.text(f'CREATE DATABASE "{database_name}"'),
        )
    await engine.dispose()


async def drop_database(url: sqlalchemy.engine.URL) -> None:
    """Drop create database."""
    dbms_url = url.set(database="postgres")
    engine = sqlalchemy.ext.asyncio.create_async_engine(
        dbms_url,
        # Needed to avoid error
        # DROP DATABASE cannot run inside a transaction block
        isolation_level="AUTOCOMMIT",
    )
    async with engine.connect() as connection:
        await connection.execute(
            sqlalchemy.text(f'DROP DATABASE "{url.database}"'),
        )
