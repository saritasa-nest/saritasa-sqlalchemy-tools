import collections.abc

import pytest

import saritasa_sqlalchemy_tools

from . import factories, models, repositories


@pytest.fixture(scope="session", autouse=True)
def anyio_backend() -> str:
    """Specify async backend."""
    return "asyncio"


@pytest.fixture(scope="session")
def manual_database_setup() -> collections.abc.Callable[..., None]:
    """Just to check that manual setup is called during setup."""
    return lambda connection: print("Manual setup done")  # noqa: T201


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
