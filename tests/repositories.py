import typing

import saritasa_sqlalchemy_tools

from . import models


class RelatedModelRepository(
    saritasa_sqlalchemy_tools.BaseRepository[models.RelatedModel],
):
    """Repository for `RelatedModel` model."""

    model: typing.TypeAlias = models.RelatedModel
    default_exclude_bulk_create_fields = (
        "created",
        "modified",
        "id",
    )
    default_exclude_bulk_update_fields = (
        "created",
        "modified",
    )


class TestModelRepository(
    saritasa_sqlalchemy_tools.BaseRepository[models.TestModel],
):
    """Repository for `TestModel` model."""

    model: typing.TypeAlias = models.TestModel
    default_exclude_bulk_create_fields = (
        "created",
        "modified",
        "id",
    )
    default_exclude_bulk_update_fields = (
        "created",
        "modified",
    )


class SoftDeleteTestModelRepository(
    saritasa_sqlalchemy_tools.BaseSoftDeleteRepository[
        models.SoftDeleteTestModel
    ],
):
    """Repository for `SoftDeleteTestModel` model."""

    model: typing.TypeAlias = models.SoftDeleteTestModel
    default_exclude_bulk_create_fields = (
        "created",
        "modified",
        "id",
    )
    default_exclude_bulk_update_fields = (
        "created",
        "modified",
    )


class M2MModelRepository(
    saritasa_sqlalchemy_tools.BaseRepository[models.M2MModel],
):
    """Repository for `M2MModel` model."""

    model: typing.TypeAlias = models.M2MModel
    default_exclude_bulk_create_fields = (
        "created",
        "modified",
        "id",
    )
    default_exclude_bulk_update_fields = (
        "created",
        "modified",
    )
