import re

import pytest

import sqlalchemy

import saritasa_sqlalchemy_tools

from . import factories, models, repositories


async def test_init_other(
    repository: repositories.TestModelRepository,
) -> None:
    """Test init other."""
    new_repo = repository.init_other(
        repositories.SoftDeleteTestModelRepository,
    )
    assert isinstance(new_repo, repositories.SoftDeleteTestModelRepository)
    assert new_repo.db_session is repository.db_session


async def test_soft_delete(
    soft_delete_test_model: models.SoftDeleteTestModel,
    soft_delete_repository: repositories.SoftDeleteTestModelRepository,
) -> None:
    """Test soft deletion, model instance should be still present in db."""
    await soft_delete_repository.delete(soft_delete_test_model)
    soft_deleted_object = await soft_delete_repository.fetch_first(
        id=soft_delete_test_model.id,
    )
    assert soft_deleted_object
    assert soft_deleted_object.deleted


async def test_force_soft_delete(
    soft_delete_test_model: models.SoftDeleteTestModel,
    soft_delete_repository: repositories.SoftDeleteTestModelRepository,
) -> None:
    """Test force soft delete."""
    await soft_delete_repository.force_delete(soft_delete_test_model)
    assert not await soft_delete_repository.fetch_first(
        id=soft_delete_test_model.id,
    )


async def test_insert_batch(
    related_model: models.RelatedModel,
    repository: repositories.TestModelRepository,
) -> None:
    """Test batch insert."""
    instances = factories.TestModelFactory.build_batch(
        related_model_id=related_model.id,
        size=5,
    )
    created_instances = await repository.insert_batch(instances)
    for created_instance in created_instances:
        assert created_instance.id
        assert created_instance.created
        assert created_instance.modified
        assert created_instance.related_model_id == related_model.id


async def test_update_batch(
    test_model_list: list[models.TestModel],
    related_model: models.RelatedModel,
    repository: repositories.TestModelRepository,
) -> None:
    """Test batch update."""
    for test_model in test_model_list:
        test_model.related_model_id = related_model.id
    await repository.update_batch(test_model_list)
    for test_model in test_model_list:
        pk = test_model.id
        repository.expire(test_model)
        test_model = await repository.fetch_first(id=pk)  # type: ignore
        assert test_model.related_model_id == related_model.id


async def test_delete_batch(
    test_model_list: list[models.TestModel],
    repository: repositories.TestModelRepository,
) -> None:
    """Test batch delete."""
    ids = [test_model.id for test_model in test_model_list]
    await repository.delete_batch(where=[models.TestModel.id.in_(ids)])
    assert not await repository.count(where=[models.TestModel.id.in_(ids)])


async def test_save(
    related_model: models.RelatedModel,
    repository: repositories.TestModelRepository,
) -> None:
    """Test that repository properly saves instances."""
    new_test_model = factories.TestModelFactory.build(
        related_model_id=related_model.id,
    )
    new_test_model = await repository.save(new_test_model, refresh=True)
    assert await repository.fetch_first(id=new_test_model.id)


async def test_expire(
    test_model: models.TestModel,
    repository: repositories.TestModelRepository,
) -> None:
    """Test that repository properly expires instances."""
    repository.expire(test_model)
    with pytest.raises(sqlalchemy.exc.MissingGreenlet):
        _ = test_model.id


@pytest.mark.parametrize(
    "reuse_select_statement",
    [
        True,
        False,
    ],
)
async def test_ordering(
    test_model_list: list[models.TestModel],
    repository: repositories.TestModelRepository,
    reuse_select_statement: bool,
) -> None:
    """Test ordering."""
    ordered_models = sorted(
        test_model_list,
        key=lambda instance: instance.text.lower(),
    )
    if reuse_select_statement:
        select_statement = repository.get_order_statement(
            None,
            *["text"],
        )
        models_from_db = await repository.fetch_all(statement=select_statement)
    else:
        models_from_db = await repository.fetch_all(ordering_clauses=["text"])
    for actual, expected in zip(models_from_db, ordered_models, strict=False):
        assert actual.id == expected.id


async def test_ordering_with_enum(
    test_model_list: list[models.TestModel],
    repository: repositories.TestModelRepository,
) -> None:
    """Test ordering with enum."""
    ordered_models = sorted(
        test_model_list,
        key=lambda instance: instance.text.lower(),
        reverse=True,
    )

    class OrderingEnum(saritasa_sqlalchemy_tools.OrderingEnum):
        text = "text"

    models_from_db = await repository.fetch_all(
        ordering_clauses=[OrderingEnum.text_desc],
    )
    for actual, expected in zip(models_from_db, ordered_models, strict=False):
        assert actual.id == expected.id


@pytest.mark.parametrize(
    "reuse_select_statement",
    [
        True,
        False,
    ],
)
async def test_pagination(
    test_model_list: list[models.TestModel],
    repository: repositories.TestModelRepository,
    reuse_select_statement: bool,
) -> None:
    """Test pagination."""
    ordered_models = sorted(
        test_model_list,
        key=lambda instance: instance.id,
    )
    args = {
        "limit": 2,
        "offset": 1,
    }
    if reuse_select_statement:
        select_statement = repository.get_pagination_statement(**args)  # type: ignore
        models_from_db = await repository.fetch_all(
            statement=select_statement,
            ordering_clauses=["id"],
        )
    else:
        models_from_db = (
            await repository.fetch_all(ordering_clauses=["id"], **args)  # type: ignore
        )
    assert models_from_db[0].id == ordered_models[1].id
    assert models_from_db[1].id == ordered_models[2].id


@pytest.mark.parametrize(
    "prefetch_type",
    [
        "select_in_load",
        "joined_load",
    ],
)
@pytest.mark.parametrize(
    "reuse_select_statement",
    [
        True,
        False,
    ],
)
async def test_prefetch(
    test_model: models.TestModel,
    repository: repositories.TestModelRepository,
    prefetch_type: str,
    reuse_select_statement: bool,
) -> None:
    """Test prefetching of related fields of model."""
    await factories.RelatedModelFactory.create_batch_async(
        session=repository.db_session,
        test_model_id=test_model.pk,
        size=5,
    )
    await factories.TestModelFactory.create_batch_async(
        session=repository.db_session,
        related_model_id=test_model.related_model_id,
        size=3,
    )
    targets = (
        models.TestModel.related_model,
        models.TestModel.related_model_nullable,
        models.TestModel.related_models,
        (
            models.TestModel.related_model,
            models.RelatedModel.test_model_list,
        ),
    )
    args = {
        "id": test_model.id,
        prefetch_type: targets,
    }
    if reuse_select_statement:
        select_statement = getattr(
            repository,
            f"get_{prefetch_type}_statement",
        )(None, *targets)
        instance = await repository.fetch_first(
            statement=select_statement,
            id=test_model.pk,
        )
    else:
        instance = await repository.fetch_first(**args)  # type: ignore
    assert instance
    assert instance.related_model
    assert not instance.related_model_nullable
    assert len(instance.related_models) == 5
    # Original plus created.
    assert len(instance.related_model.test_model_list) == 4


@pytest.mark.parametrize(
    "reuse_select_statement",
    [
        True,
        False,
    ],
)
async def test_filter_in(
    test_model_list: list[models.TestModel],
    repository: repositories.TestModelRepository,
    reuse_select_statement: bool,
) -> None:
    """Test filter `in`."""
    filtered_models = list(
        filter(
            lambda instance: instance.text
            in [test_model_list[0].text, test_model_list[3].text],
            test_model_list,
        ),
    )
    args = {
        "where": [
            saritasa_sqlalchemy_tools.Filter(
                field="text__in",
                value=[test_model_list[0].text, test_model_list[3].text],
            ),
        ],
    }
    if reuse_select_statement:
        select_statement = repository.get_filter_statement(
            None,
            *args["where"],
        )
        instances = await repository.fetch_all(
            statement=select_statement,
            ordering_clauses=["id"],
        )
    else:
        instances = await repository.fetch_all(
            **args,  # type: ignore
            ordering_clauses=["id"],
        )
    assert instances[0].id == filtered_models[0].id
    assert instances[1].id == filtered_models[1].id


@pytest.mark.parametrize(
    "reuse_select_statement",
    [
        True,
        False,
    ],
)
async def test_filter_in_exclude(
    test_model_list: list[models.TestModel],
    repository: repositories.TestModelRepository,
    reuse_select_statement: bool,
) -> None:
    """Test filter `in` with exclude."""
    filtered_models = list(
        filter(
            lambda instance: instance.text
            in [test_model_list[0].text, test_model_list[3].text],
            test_model_list,
        ),
    )
    args = {
        "where": [
            saritasa_sqlalchemy_tools.Filter(
                field="text__in",
                value=[test_model_list[0].text, test_model_list[3].text],
                exclude=True,
            ),
        ],
    }
    if reuse_select_statement:
        select_statement = repository.get_filter_statement(
            None,
            *args["where"],
        )
        instances = await repository.fetch_all(
            statement=select_statement,
            ordering_clauses=["id"],
        )
    else:
        instances = await repository.fetch_all(
            **args,  # type: ignore
            ordering_clauses=["id"],
        )
    assert len(instances) == len(test_model_list) - len(filtered_models)
    instance_ids = [instance.id for instance in instances]
    assert filtered_models[0].id not in instance_ids
    assert filtered_models[1].id not in instance_ids


@pytest.mark.parametrize(
    "reuse_select_statement",
    [
        True,
        False,
    ],
)
async def test_filter_in_as_kwargs(
    test_model_list: list[models.TestModel],
    repository: repositories.TestModelRepository,
    reuse_select_statement: bool,
) -> None:
    """Test filter `in` as kwargs."""
    filtered_models = list(
        filter(
            lambda instance: instance.text
            in [test_model_list[0].text, test_model_list[3].text],
            test_model_list,
        ),
    )
    kwargs = {
        "text__in": [test_model_list[0].text, test_model_list[3].text],
    }
    if reuse_select_statement:
        select_statement = repository.get_filter_statement(
            None,
            **kwargs,
        )
        instances = await repository.fetch_all(
            statement=select_statement,
            ordering_clauses=["id"],
        )
    else:
        instances = await repository.fetch_all(
            **kwargs,  # type: ignore
            ordering_clauses=["id"],
        )
    assert instances[0].id == filtered_models[0].id
    assert instances[1].id == filtered_models[1].id


@pytest.mark.parametrize(
    "reuse_select_statement",
    [
        True,
        False,
    ],
)
async def test_filter_not_in_as_kwargs(
    test_model_list: list[models.TestModel],
    repository: repositories.TestModelRepository,
    reuse_select_statement: bool,
) -> None:
    """Test filter exclude `in` as kwargs."""
    filtered_models = list(
        filter(
            lambda instance: instance.text
            in [test_model_list[0].text, test_model_list[3].text],
            test_model_list,
        ),
    )
    kwargs = {
        "text__not_in": [test_model_list[0].text, test_model_list[3].text],
    }
    if reuse_select_statement:
        select_statement = repository.get_filter_statement(
            None,
            **kwargs,
        )
        instances = await repository.fetch_all(
            statement=select_statement,
            ordering_clauses=["id"],
        )
    else:
        instances = await repository.fetch_all(
            **kwargs,  # type: ignore
            ordering_clauses=["id"],
        )
    assert len(instances) == len(test_model_list) - len(filtered_models)
    instance_ids = [instance.id for instance in instances]
    assert filtered_models[0].id not in instance_ids
    assert filtered_models[1].id not in instance_ids


@pytest.mark.parametrize(
    "reuse_select_statement",
    [
        True,
        False,
    ],
)
async def test_filter_gte(
    test_model_list: list[models.TestModel],
    repository: repositories.TestModelRepository,
    reuse_select_statement: bool,
) -> None:
    """Test filter `gte`."""
    max_num = max(test_model.number for test_model in test_model_list)

    args = {
        "where": [
            saritasa_sqlalchemy_tools.Filter(
                field="number__gte",
                value=max_num,
            ),
        ],
    }
    if reuse_select_statement:
        select_statement = repository.get_filter_statement(
            None,
            *args["where"],
        )
        instances = await repository.fetch_all(
            statement=select_statement,
            ordering_clauses=["id"],
        )
    else:
        instances = await repository.fetch_all(
            **args,  # type: ignore
            ordering_clauses=["id"],
        )
    assert len(instances) == 1
    assert instances[0].number == max_num


@pytest.mark.parametrize(
    "reuse_select_statement",
    [
        True,
        False,
    ],
)
async def test_filter_m2m(
    test_model: models.TestModel,
    repository: repositories.TestModelRepository,
    reuse_select_statement: bool,
) -> None:
    """Test filter related to m2m fields."""
    await factories.M2MModelFactory.create_batch_async(
        session=repository.db_session,
        size=5,
        test_model_id=test_model.pk,
        related_model_id=test_model.related_model_id,
    )
    await factories.M2MModelFactory.create_batch_async(
        session=repository.db_session,
        size=5,
    )

    args = {
        "where": [
            saritasa_sqlalchemy_tools.Filter(
                field="m2m_related_models__id__in",
                value=[test_model.related_model_id],
            ),
        ],
    }
    if reuse_select_statement:
        select_statement = repository.get_filter_statement(
            None,
            *args["where"],
        )
        instances = await repository.fetch_all(
            statement=select_statement,
            ordering_clauses=["id"],
        )
    else:
        instances = await repository.fetch_all(
            **args,  # type: ignore
            ordering_clauses=["id"],
        )
    assert len(instances) == 1
    assert instances[0].id == test_model.id


async def test_search_filter(
    test_model_list: list[models.TestModel],
    repository: repositories.TestModelRepository,
) -> None:
    """Test search filter."""
    search_text = test_model_list[0].text
    instances = await repository.fetch_all(
        where=[
            saritasa_sqlalchemy_tools.transform_search_filter(
                models.TestModel,
                search_fields=[
                    "text",
                    "id",
                ],
                value=search_text,
            ),
        ],
        ordering_clauses=["id"],
    )
    assert len(instances) == 1, [instance.text for instance in instances]
    assert instances[0].id == test_model_list[0].id


@pytest.mark.parametrize(
    "reuse_select_statement",
    [
        True,
        False,
    ],
)
async def test_annotation(
    test_model: models.TestModel,
    repository: repositories.TestModelRepository,
    reuse_select_statement: bool,
) -> None:
    """Test annotations loading."""
    await factories.RelatedModelFactory.create_batch_async(
        session=repository.db_session,
        size=5,
        test_model_id=test_model.pk,
    )
    annotations = (models.TestModel.related_models_count,)
    if reuse_select_statement:
        select_statement = repository.get_annotated_statement(
            None,
            *annotations,
        )
        instance = await repository.fetch_first(
            statement=select_statement,
            id=test_model.pk,
        )
    else:
        instance = await repository.fetch_first(
            id=test_model.pk,
            annotations=annotations,
        )
    assert instance
    assert (
        instance.related_models_count
        == await repository.init_other(
            repositories.RelatedModelRepository,
        ).count()
    )


async def test_annotation_query(
    test_model: models.TestModel,
    repository: repositories.TestModelRepository,
) -> None:
    """Test annotations loading when using dynamic queries."""
    instance = await repository.fetch_first(
        id=test_model.pk,
        annotations=(
            (
                models.TestModel.related_models_count_query,
                sqlalchemy.select(
                    sqlalchemy.func.count(models.RelatedModel.id),
                )
                .where(
                    models.RelatedModel.test_model_id == models.TestModel.id,
                )
                .correlate_except(models.RelatedModel)
                .scalar_subquery(),
            ),
        ),
        select_in_load=(models.TestModel.related_models,),
    )
    assert instance
    assert instance.related_models_count_query == len(
        test_model.related_models,
    )


async def test_values(
    test_model_list: list[models.TestModel],
    repository: repositories.TestModelRepository,
) -> None:
    """Test values method."""
    excepted_text_values = {test_model.text for test_model in test_model_list}
    actual_text_values = set(
        await repository.values(
            field=models.TestModel.text,
        ),
    )
    assert excepted_text_values == actual_text_values


async def test_filter_related_models_has(
    test_model: models.TestModel,
    test_model_list: list[models.TestModel],
    repository: repositories.TestModelRepository,
) -> None:
    """Test filtration thought related models via one-to-many."""
    await factories.RelatedModelFactory.create_batch_async(
        session=repository.db_session,
        size=5,
    )
    related_model = await factories.RelatedModelFactory.create_async(
        session=repository.db_session,
        test_model_id=test_model.pk,
    )
    new_test_model = await factories.TestModelFactory.create_async(
        session=repository.db_session,
        related_model_id=related_model.pk,
    )
    result = await repository.fetch_all(
        where=(
            saritasa_sqlalchemy_tools.Filter(
                field="related_model__test_model__text__exact",
                value=test_model.text,
            ),
        ),
    )
    assert len(result) == 1
    assert result[0].id == new_test_model.id
    assert result[0].related_model_id == new_test_model.related_model_id


async def test_filter_related_models_any(
    test_model: models.TestModel,
    test_model_list: list[models.TestModel],
    repository: repositories.TestModelRepository,
) -> None:
    """Test filtration thought related models via many-to-one."""
    await factories.RelatedModelFactory.create_batch_async(
        session=repository.db_session,
        size=5,
    )
    related_models = await factories.RelatedModelFactory.create_batch_async(
        session=repository.db_session,
        size=5,
        test_model_id=test_model.pk,
    )
    new_test_model = await factories.TestModelFactory.create_async(
        session=repository.db_session,
        related_model_id=related_models[0].pk,
    )

    result = await repository.fetch_all(
        where=(
            saritasa_sqlalchemy_tools.Filter(
                field="related_models__test_model_list__text__exact",
                value=new_test_model.text,
            ),
        ),
    )
    assert len(result) == 1
    assert result[0].id == test_model.id


async def test_filter_invalid_filter_arg(
    test_model_list: list[models.TestModel],
    repository: repositories.TestModelRepository,
) -> None:
    """Test when filter args has too many `__`."""
    with pytest.raises(
        ValueError,
        match=re.escape("Long filter args only supported for relationships!"),
    ):
        await repository.fetch_all(
            where=(
                saritasa_sqlalchemy_tools.Filter(
                    field="text__exact__in",
                    value="Test",
                ),
            ),
        )
