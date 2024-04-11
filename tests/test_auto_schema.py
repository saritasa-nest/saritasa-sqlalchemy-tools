import datetime
import decimal
import re
import typing

import pydantic
import pytest

import saritasa_sqlalchemy_tools

from . import models, repositories

SPECIAL_POSTGRES_TYPES = {
    saritasa_sqlalchemy_tools.PostgresRange[datetime.date],
}


@pytest.mark.parametrize(
    "field",
    [
        "id",
        "created",
        "modified",
        "text",
        "text_nullable",
        "text_enum",
        "text_enum_nullable",
        "number",
        "number_nullable",
        "small_number",
        "small_number_nullable",
        "decimal_number",
        "decimal_number_nullable",
        "boolean",
        "boolean_nullable",
        "text_list",
        "text_list_nullable",
        "date_time",
        "date_time_nullable",
        "date",
        "date_nullable",
        "timedelta",
        "timedelta_nullable",
        "related_model_id",
        "related_model_id_nullable",
        "custom_property",
        "custom_property_nullable",
        "json_field",
        "json_field_nullable",
        "date_range",
        "date_range_nullable",
    ],
)
async def test_auto_schema_generation(
    test_model: models.TestModel,
    field: str,
) -> None:
    """Test schema generation picks correct types from model for schema."""

    class AutoSchema(saritasa_sqlalchemy_tools.ModelAutoSchema):
        class Meta:
            model = models.TestModel
            model_config = pydantic.ConfigDict(
                from_attributes=True,
                validate_assignment=True,
            )
            fields = (field,)

    schema = AutoSchema.get_schema()
    model = schema.model_validate(test_model)
    value = getattr(model, field)
    if value.__class__ in SPECIAL_POSTGRES_TYPES:
        value = value.to_db()
    assert value == getattr(test_model, field)
    if "nullable" not in field and "property" not in field:
        with pytest.raises(pydantic.ValidationError):
            setattr(model, field, None)


@pytest.mark.parametrize(
    [
        "field",
        "field_type",
    ],
    [
        ["text", str | None],
        ["text_enum", models.TestModel.TextEnum | None],
        ["number", int | None],
        ["small_number", int | None],
        ["decimal_number", decimal.Decimal | None],
        ["boolean", bool | None],
        ["text_list", list[str] | None],
        ["date_time", datetime.datetime | None],
        ["date", datetime.date | None],
        ["timedelta", datetime.timedelta | None],
        ["json_field", dict[str, typing.Any] | None],
        ["custom_property", str | None],
        ["related_model_id", int | None],
        [
            "date_range",
            saritasa_sqlalchemy_tools.PostgresRange[datetime.date] | None,
        ],
    ],
)
async def test_auto_schema_type_override_generation(
    test_model: models.TestModel,
    field: str,
    field_type: type,
) -> None:
    """Test that in auto schema generation you can override type.

    Check if you specify type for field like this (field, type), then schema
    generation will ignore type from model, and will use specified one.

    """

    class AutoSchema(saritasa_sqlalchemy_tools.ModelAutoSchema):
        class Meta:
            model = models.TestModel
            fields = (
                (
                    field,
                    field_type,
                ),
            )

    schema = AutoSchema.get_schema()
    model = schema.model_validate(test_model)
    if "property" not in field:
        setattr(model, field, None)


async def test_auto_schema_type_invalid_field_config(
    test_model: models.TestModel,
) -> None:
    """Test than on invalid field config type there is an error.

    Check that if use any type other than str or tuple[str, type], schema
    generation will raise an error.

    """

    class AutoSchema(saritasa_sqlalchemy_tools.ModelAutoSchema):
        class Meta:
            model = models.TestModel
            fields = (("id", int, 1),)

    with pytest.raises(
        saritasa_sqlalchemy_tools.schema.UnableProcessTypeError,
        match=re.escape(
            "Can't process the following field ('id', <class 'int'>, 1)",
        ),
    ):
        AutoSchema.get_schema()


async def test_auto_schema_related_field_with_no_schema(
    test_model: models.TestModel,
) -> None:
    """Test that in generation raise error on relationships without type.

    For relationship field developer must specify type, otherwise generation
    must throw an error.

    """

    class AutoSchema(saritasa_sqlalchemy_tools.ModelAutoSchema):
        class Meta:
            model = models.TestModel
            fields = (
                "related_model",
                "related_models",
            )

    with pytest.raises(
        saritasa_sqlalchemy_tools.schema.UnableProcessTypeError,
        match=re.escape(
            "Schema generation is not supported for relationship "
            "fields(related_model), please use auto-schema or pydantic class",
        ),
    ):
        AutoSchema.get_schema()


async def test_auto_schema_related_field_with_schema(
    test_model: models.TestModel,
    repository: repositories.TestModelRepository,
) -> None:
    """Test that generation works correctly with related types auto.

    Verify that ModelAutoSchema can be used as a type.

    """

    class RelatedAutoSchema(saritasa_sqlalchemy_tools.ModelAutoSchema):
        class Meta:
            model = models.RelatedModel
            fields = (
                "id",
                "created",
                "modified",
            )

    class AutoSchema(saritasa_sqlalchemy_tools.ModelAutoSchema):
        class Meta:
            model = models.TestModel
            fields = (
                ("related_model", RelatedAutoSchema),
                ("related_model_nullable", RelatedAutoSchema),
                ("related_models", RelatedAutoSchema),
                ("custom_property_related_model", RelatedAutoSchema),
                ("custom_property_related_model_nullable", RelatedAutoSchema),
                ("custom_property_related_models", RelatedAutoSchema),
            )

    schema = AutoSchema.get_schema()
    instance = await repository.fetch_first(
        id=test_model.pk,
        select_in_load=(
            models.TestModel.related_model,
            models.TestModel.related_model_nullable,
            models.TestModel.related_models,
        ),
    )
    model = schema.model_validate(instance)
    isinstance(model.related_models, list)
    for field in RelatedAutoSchema.Meta.fields:
        assert getattr(
            model.related_model,
            field,
        ) == getattr(
            test_model.related_model,
            field,
        )
        for related_model, test_related_model in zip(
            model.related_models,
            test_model.related_models,
            strict=False,
        ):
            assert getattr(
                related_model,
                field,
            ) == getattr(
                test_related_model,
                field,
            )


async def test_auto_schema_use_both_config_and_model() -> None:
    """Test schema generation fails when both config and model are used.

    It's not allowed to specify both model config and base model in Meta.

    """

    class AutoSchema(saritasa_sqlalchemy_tools.ModelAutoSchema):
        class Meta:
            model = models.TestModel
            model_config = pydantic.ConfigDict(
                from_attributes=True,
                validate_assignment=True,
            )
            base_model = pydantic.BaseModel
            fields = (
                "id",
                "created",
                "modified",
            )

    with pytest.raises(
        ValueError,
        match=re.escape(
            "Only config or base model could be passed to create_model",
        ),
    ):
        AutoSchema.get_schema()


async def test_auto_schema_use_model() -> None:
    """Test schema generation works when base model is specified."""

    class AutoSchema(saritasa_sqlalchemy_tools.ModelAutoSchema):
        class Meta:
            model = models.TestModel
            base_model = pydantic.BaseModel
            fields = (
                "id",
                "created",
                "modified",
            )

    AutoSchema.get_schema()


def custom_validator(
    cls,  # noqa: ANN001
    value: typing.Any,
    info: pydantic.ValidationInfo,
) -> None:
    """Raise value error."""
    raise ValueError("This is custom validator")


def test_custom_field_validators(
    test_model: models.TestModel,
) -> None:
    """Test field validators for schema generation.

    Verify that schema generation would assign validators from
    extra_fields_validators for each field.

    """

    class AutoSchema(saritasa_sqlalchemy_tools.ModelAutoSchema):
        class Meta:
            model = models.TestModel
            fields = ("id",)
            extra_fields_validators: typing.ClassVar = {
                "id": (custom_validator,),
            }

    schema = AutoSchema.get_schema()
    with pytest.raises(
        pydantic.ValidationError,
        match=re.escape("This is custom validator"),
    ):
        schema.model_validate(test_model)


def test_custom_field_validators_custom_type(
    test_model: models.TestModel,
) -> None:
    """Test field validators for schema generation(custom type case).

    Same as test_custom_field_validators, but in this case custom type is used.

    """

    class AutoSchema(saritasa_sqlalchemy_tools.ModelAutoSchema):
        class Meta:
            model = models.TestModel
            fields = (("id", int),)
            extra_fields_validators: typing.ClassVar = {
                "id": (custom_validator,),
            }

    schema = AutoSchema.get_schema()
    with pytest.raises(
        pydantic.ValidationError,
        match=re.escape("This is custom validator"),
    ):
        schema.model_validate(test_model)


def test_custom_field_validators_property(
    test_model: models.TestModel,
) -> None:
    """Test field validators for property for schema generation.

    Verify that schema generation correctly works with models @property attrs

    """

    class AutoSchema(saritasa_sqlalchemy_tools.ModelAutoSchema):
        class Meta:
            model = models.TestModel
            fields = ("custom_property_related_model",)
            extra_fields_validators: typing.ClassVar = {
                "custom_property_related_model": (custom_validator,),
            }

    schema = AutoSchema.get_schema()
    with pytest.raises(
        pydantic.ValidationError,
        match=re.escape("This is custom validator"),
    ):
        schema.model_validate(test_model)


def test_custom_field_validators_property_custom_type(
    test_model: models.TestModel,
) -> None:
    """Test validators for property for schema generation(custom type case).

    Same as test_custom_field_validators_property, but custom type is
    specified.

    """

    class AutoSchema(saritasa_sqlalchemy_tools.ModelAutoSchema):
        class Meta:
            model = models.TestModel
            fields = (("custom_property_related_model", typing.Any),)
            extra_fields_validators: typing.ClassVar = {
                "custom_property_related_model": (custom_validator,),
            }

    schema = AutoSchema.get_schema()
    with pytest.raises(
        pydantic.ValidationError,
        match=re.escape("This is custom validator"),
    ):
        schema.model_validate(test_model)


def test_postgres_range_validation() -> None:
    """Test that bound validation works for PostgresRange."""
    with pytest.raises(
        pydantic.ValidationError,
        match=re.escape("Lower must be equal or less than upper limit"),
    ):
        saritasa_sqlalchemy_tools.PostgresRange(
            lower=10,
            upper=1,
        )
