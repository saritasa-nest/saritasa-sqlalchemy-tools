# pragma: no cover
import collections.abc
import contextlib
import typing

import sqlalchemy
import sqlalchemy.event
import sqlalchemy.ext.asyncio
import sqlalchemy.orm

Session: typing.TypeAlias = sqlalchemy.ext.asyncio.AsyncSession
SessionFactory: typing.TypeAlias = collections.abc.Callable[
    [],
    collections.abc.AsyncIterator[Session],
]
SessionOnConnect = collections.abc.Callable[..., None]


def set_search_path(
    dbapi_connection,  # noqa: ANN001
    connection_record,  # noqa: ANN001
    schema: str,
) -> None:
    """Set search path to schema on connect."""
    existing_autocommit = dbapi_connection.autocommit
    dbapi_connection.autocommit = True
    cursor = dbapi_connection.cursor()
    cursor.execute(f"SET SESSION search_path='{schema}'")
    cursor.close()
    dbapi_connection.commit()
    dbapi_connection.autocommit = existing_autocommit


def get_async_engine(
    drivername: str,
    username: str,
    password: str,
    host: str,
    port: int,
    database: str,
    query: dict[str, tuple[str, ...] | str],
    echo: bool = False,
    on_connect: collections.abc.Sequence[SessionOnConnect] = (),
) -> sqlalchemy.ext.asyncio.AsyncEngine:
    """Set up engine for working with database."""
    db_engine = sqlalchemy.ext.asyncio.create_async_engine(
        sqlalchemy.engine.URL(
            drivername=drivername,
            username=username,
            password=password,
            host=host,
            port=port,
            database=database,
            query=query,  # type: ignore
        ),
        echo=echo,
    )
    for on_connect_func in on_connect:
        sqlalchemy.event.listens_for(
            target=db_engine.sync_engine,
            identifier="connect",
            insert=True,
        )(on_connect_func)
    return db_engine


def get_async_session_factory(
    drivername: str,
    username: str,
    password: str,
    host: str,
    port: int,
    database: str,
    query: dict[str, tuple[str, ...] | str],
    echo: bool = False,
    on_connect: collections.abc.Sequence[SessionOnConnect] = (),
    autocommit: bool = False,
    # The Session.commit() operation unconditionally issues Session.flush()
    # before emitting COMMIT on relevant database connections.
    # If no pending changes are detected, then no SQL is emitted to the
    # database. This behavior is not configurable and is not affected by
    # the Session.autoflush parameter.
    autoflush: bool = False,
    expire_on_commit: bool = False,
) -> sqlalchemy.ext.asyncio.async_sessionmaker[
    sqlalchemy.ext.asyncio.AsyncSession
]:
    """Set up session factory."""
    return sqlalchemy.ext.asyncio.async_sessionmaker(
        bind=get_async_engine(
            drivername=drivername,
            username=username,
            password=password,
            host=host,
            port=port,
            database=database,
            on_connect=on_connect,
            echo=echo,
            query=query,
        ),
        autocommit=autocommit,
        autoflush=autoflush,
        expire_on_commit=expire_on_commit,
    )


async def get_async_db_session(
    drivername: str,
    username: str,
    password: str,
    host: str,
    port: int,
    database: str,
    query: dict[str, tuple[str, ...] | str],
    echo: bool = False,
    on_connect: collections.abc.Sequence[SessionOnConnect] = (),
    autocommit: bool = False,
    autoflush: bool = False,
    expire_on_commit: bool = False,
) -> collections.abc.AsyncIterator[Session]:
    """Set up and get db session."""
    async with get_async_session_factory(
        drivername=drivername,
        username=username,
        password=password,
        host=host,
        port=port,
        database=database,
        on_connect=on_connect,
        echo=echo,
        autocommit=autocommit,
        autoflush=autoflush,
        expire_on_commit=expire_on_commit,
        query=query,
    )() as session:
        try:
            yield session
        except Exception as error:
            await session.rollback()
            raise error
        else:
            await session.commit()


@contextlib.asynccontextmanager
async def get_async_db_session_context(
    drivername: str,
    username: str,
    password: str,
    host: str,
    port: int,
    database: str,
    query: dict[str, tuple[str, ...] | str],
    echo: bool = False,
    on_connect: collections.abc.Sequence[SessionOnConnect] = (),
    autocommit: bool = False,
    autoflush: bool = False,
    expire_on_commit: bool = False,
) -> collections.abc.AsyncIterator[Session]:
    """Init db session."""
    db_iterator = get_async_db_session(
        drivername=drivername,
        username=username,
        password=password,
        host=host,
        port=port,
        database=database,
        on_connect=on_connect,
        echo=echo,
        autocommit=autocommit,
        autoflush=autoflush,
        expire_on_commit=expire_on_commit,
        query=query,
    )
    try:
        yield await anext(db_iterator)  # type: ignore
    finally:
        await anext(db_iterator, None)
