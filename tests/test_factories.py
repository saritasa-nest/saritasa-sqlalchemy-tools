import pytest

import saritasa_sqlalchemy_tools

from . import factories, models, repositories


async def test_factory_missing_repository(
    db_session: saritasa_sqlalchemy_tools.Session,
    repository: repositories.TestModelRepository,
) -> None:
    """Test that error is raised if repository class missing."""

    class TestModelFactory(
        saritasa_sqlalchemy_tools.AsyncSQLAlchemyModelFactory[
            models.TestModel
        ],
    ):
        """Factory to generate TestModel."""

        class Meta:
            model = models.TestModel

    with pytest.raises(
        ValueError,
        match="Repository class is not set in Meta class",
    ):
        await TestModelFactory.create_async(db_session)


async def test_factory_generation(
    db_session: saritasa_sqlalchemy_tools.Session,
    repository: repositories.TestModelRepository,
) -> None:
    """Test that model generation works as expected."""
    instance = await factories.TestModelFactory.create_async(db_session)
    assert await repository.exists(id=instance.id)


async def test_factory_generation_sub_factories(
    db_session: saritasa_sqlalchemy_tools.Session,
    repository: repositories.TestModelRepository,
) -> None:
    """Test that model generation works with sub factories as expected.

    It should create and attach all related models.

    """
    instance = await factories.TestModelFactory.create_async(db_session)
    instance_created = (
        await repository.fetch(
            id=instance.id,
            select_in_load=(
                models.TestModel.related_model,
                models.TestModel.related_models,
            ),
        )
    ).first()
    assert instance_created
    assert instance_created.related_model_id
    assert instance_created.related_model
    assert len(instance_created.related_models) == 5


async def test_factory_generation_skip_sub_factories(
    db_session: saritasa_sqlalchemy_tools.Session,
    repository: repositories.TestModelRepository,
) -> None:
    """Test that sub_factory will be skipped if value is passed.

    If passed value for fields which are generated via sub-factories,
    sub-factories should be called.

    """
    await factories.TestModelFactory.create_async(
        db_session,
        related_model=await factories.RelatedModelFactory.create_async(
            db_session,
        ),
        related_models=await factories.RelatedModelFactory.create_batch_async(
            db_session,
            size=3,
        ),
    )
    assert await repositories.RelatedModelRepository(db_session).count() == 4


async def test_factory_generation_skip_sub_factories_id_passed(
    db_session: saritasa_sqlalchemy_tools.Session,
    repository: repositories.TestModelRepository,
) -> None:
    """Test that sub_factory will be skipped if fk id is passed.

    Same as test_factory_generation_skip_sub_factories, but in this case we
    pass id of related object.

    """
    await factories.TestModelFactory.create_async(
        db_session,
        related_model_id=(
            await factories.RelatedModelFactory.create_async(
                db_session,
            )
        ).id,
        related_models=[],
    )
    assert await repositories.RelatedModelRepository(db_session).count() == 1


async def test_factory_generation_batch(
    db_session: saritasa_sqlalchemy_tools.Session,
    repository: repositories.TestModelRepository,
) -> None:
    """Test that model batch generation works as expected."""
    instances = await factories.TestModelFactory.create_batch_async(
        db_session,
        size=5,
    )
    for instance in instances:
        assert await repository.exists(id=instance.id)
