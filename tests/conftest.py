import asyncio
import collections.abc
import typing

import pytest

import sqlalchemy

import saritasa_sqlalchemy_tools

from . import factories, models, repositories


@pytest.fixture(scope="session")
def event_loop() -> (
    collections.abc.Generator[
        asyncio.AbstractEventLoop,
        typing.Any,
        None,
    ]
):
    """Override `event_loop` fixture to change scope to `session`.

    Needed for pytest-async-sqlalchemy.

    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


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
    return sqlalchemy.engine.URL(
        drivername="postgresql+asyncpg",
        username="saritasa-sqlalchemy-tools-user",
        password="manager",
        host="postgres",
        port=5432,
        database="_".join(
            filter(
                None,
                (
                    "saritasa-sqlalchemy-tools-dev",
                    "test",
                    worker_input["workerid"],
                ),
            ),
        ),
        query={},  # type: ignore
    ).render_as_string(hide_password=False)


@pytest.fixture(scope="session")
def init_database() -> collections.abc.Callable[..., None]:
    """Return callable object that will be called to init database.

    Overridden fixture from `pytest-async-sqlalchemy package`.
    https://github.com/igortg/pytest-async-sqlalchemy

    """
    return saritasa_sqlalchemy_tools.BaseModel.metadata.create_all


@pytest.fixture
async def test_model(
    db_session: saritasa_sqlalchemy_tools.Session,
) -> models.TestModel:
    """Generate test_model instance."""
    return await factories.TestModelFactory.create_async(session=db_session)


@pytest.fixture
async def related_model(
    db_session: saritasa_sqlalchemy_tools.Session,
) -> models.RelatedModel:
    """Generate test_model instance."""
    return await factories.RelatedModelFactory.create_async(session=db_session)


@pytest.fixture
async def test_model_list(
    db_session: saritasa_sqlalchemy_tools.Session,
) -> collections.abc.Sequence[models.TestModel]:
    """Generate test_model instances."""
    return await factories.TestModelFactory.create_batch_async(
        session=db_session,
        size=5,
    )


@pytest.fixture
async def repository(
    db_session: saritasa_sqlalchemy_tools.Session,
) -> repositories.TestModelRepository:
    """Get repository for `TestModel`."""
    return repositories.TestModelRepository(db_session=db_session)


@pytest.fixture
async def soft_delete_test_model(
    db_session: saritasa_sqlalchemy_tools.Session,
) -> models.SoftDeleteTestModel:
    """Generate `SoftDeleteTestModel` instance."""
    return await factories.SoftDeleteTestModelFactory.create_async(
        session=db_session,
    )


@pytest.fixture
async def soft_delete_repository(
    db_session: saritasa_sqlalchemy_tools.Session,
) -> repositories.SoftDeleteTestModelRepository:
    """Get soft delete repository."""
    return repositories.SoftDeleteTestModelRepository(db_session=db_session)
