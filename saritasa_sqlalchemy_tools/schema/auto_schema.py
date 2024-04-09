import collections.abc
import datetime
import decimal
import types
import typing

import pydantic
import pydantic_core
import sqlalchemy.dialects.postgresql
import sqlalchemy.orm

from .. import models
from . import fields

PydanticFieldConfig: typing.TypeAlias = tuple[
    types.UnionType
    | type[typing.Any]
    | pydantic_core.PydanticUndefinedType
    | typing.Annotated,  # type: ignore
    typing.Any,
]
MetaField: typing.TypeAlias = str | tuple[str, type]
MetaExtraFieldConfig: typing.TypeAlias = dict[str, typing.Any]
PydanticValidator: typing.TypeAlias = collections.abc.Callable[
    [typing.Any, typing.Any, pydantic.ValidationInfo],
    typing.Any,
]


class ModelAutoSchemaError(Exception):
    """Base exception for auto schema generator."""


class UnableProcessTypeError(ModelAutoSchemaError):
    """Raised when we don't know how to handle db type."""


class UnableToExtractEnumClassError(ModelAutoSchemaError):
    """Raised when we can't extract python enum class from model."""


class ModelAutoSchema:
    """Class for generating pydantic models based on sqlalchemy models.

    Create pydantic model based on fields of model specified in meta class.

    Example:
    -------
    class User(sqlalchemy.orm.DeclarativeBase):

        __tablename__ = "users"

        name: orm.Mapped[str] = orm.mapped_column(
            String(50),
            nullable=False,
        )
        location_id: orm.Mapped[int] = orm.mapped_column(
            ForeignKey("locations.id"),
            nullable=False,
        )
        location = orm.relationship(
            "Location",
            back_populates="users",
        )

    class UserAutoSchema(ModelAutoSchema):
        class Meta:
            model = User
            fields = (
                "id",
                "name",
                ("location", LocationSchema), # Use tuple to specify custom
                                              # type or for relationship
                                              # fields.
            )
            model_config = pydantic.ConfigDict(from_attributes=True)
            extra_fields_config = { # Use this to add extra field constraints
                "name": {
                    "min_length: 1,
                }
            }
            extra_fields_validators = { # Use this to assign custom validators
                "name": (validator_func1, validator_func2),
            }

    """

    class Meta:
        model: models.SQLAlchemyModel
        fields: collections.abc.Sequence[MetaField] = ()
        model_config: pydantic.ConfigDict
        base_model: pydantic.BaseModel
        extra_fields_config: dict[str, MetaExtraFieldConfig]
        extra_fields_validators: dict[
            str,
            collections.abc.Sequence[PydanticValidator],
        ]

    @classmethod
    def get_schema_name(cls) -> str:
        """Generate name for new schema class."""
        return cls.__name__.replace("AutoSchema", "")

    @classmethod
    def get_schema(
        cls,
        cls_kwargs: dict[str, typing.Any] | None = None,
    ) -> type[pydantic.BaseModel]:
        """Generate schema from model."""
        base_model = getattr(
            cls.Meta,
            "base_model",
            None,
        )
        model_config = getattr(
            cls.Meta,
            "model_config",
            None,
        )
        # Only config or base model could be passed to create_model
        if base_model and model_config:
            raise ValueError(
                "Only config or base model could be passed to create_model",
            )
        if base_model is None and model_config is None:
            model_config = pydantic.ConfigDict(from_attributes=True)

        extra_fields_config = getattr(
            cls.Meta,
            "extra_fields_config",
            {},
        )
        extra_fields_validators = getattr(
            cls.Meta,
            "extra_fields_validators",
            {},
        )
        generated_fields: dict[str, PydanticFieldConfig] = {}
        validators: dict[str, typing.Any] = {}
        for field in cls.Meta.fields:
            extra_field_config = extra_fields_config.get(field, {})
            if isinstance(field, str):
                generated_fields[field] = cls._generate_field(
                    model=cls.Meta.model,
                    field=field,
                    extra_field_config=extra_field_config,
                )
                for index, validator in enumerate(
                    extra_fields_validators.get(field, ()),
                ):
                    validators[f"{field}_validator_{index}"] = (
                        pydantic.field_validator(field)(validator)
                    )
                continue
            if isinstance(field, tuple) and len(field) == 2:
                field_name, field_type = field
                generated_fields[field_name] = (
                    cls._generate_field_with_custom_type(
                        model=cls.Meta.model,
                        field=field_name,
                        field_type=field_type,
                        extra_field_config=extra_field_config,
                    )
                )
                for index, validator in enumerate(
                    extra_fields_validators.get(field_name, ()),
                ):
                    validators[f"{field_name}_validator_{index}"] = (
                        pydantic.field_validator(field_name)(validator)
                    )
                continue
            raise UnableProcessTypeError(
                f"Can't process the following field {field}",
            )
        return pydantic.create_model(
            cls.get_schema_name(),
            __base__=base_model,
            __config__=model_config,
            __validators__=validators,
            __cls_kwargs__=cls_kwargs,
            **generated_fields,  # type: ignore
        )  # type: ignore[call-overload]

    @classmethod
    def _generate_field(
        cls,
        model: models.SQLAlchemyModel,
        field: str,
        extra_field_config: MetaExtraFieldConfig,
    ) -> PydanticFieldConfig:
        """Generate field for pydantic model."""
        model_attribute: models.ModelAttribute = getattr(
            model,
            field,
        )
        types_mapping = cls._get_db_types_mapping()
        if isinstance(model_attribute, property):
            return cls._generate_property_field(
                model,
                field,
                model_attribute,
                extra_field_config,
            )
        if isinstance(model_attribute.property, sqlalchemy.orm.Relationship):
            raise UnableProcessTypeError(
                "Schema generation is not supported for relationship "
                f"fields({field}), please use auto-schema or pydantic class",
            )
        if (
            model_attribute.type.__class__ not in types_mapping
        ):  # pragma: no cover
            raise UnableProcessTypeError(
                "Can't generate generate type for"
                f" {model_attribute.type.__class__}"
                f" for field {field}",
            )
        return types_mapping[model_attribute.type.__class__](
            model,
            field,
            model_attribute,
            model_attribute.type,
            extra_field_config,
        )

    @classmethod
    def _generate_field_with_custom_type(
        cls,
        model: models.SQLAlchemyModel,
        field: str,
        field_type: typing.Any,
        extra_field_config: MetaExtraFieldConfig,
    ) -> PydanticFieldConfig:
        """Generate field with custom type."""
        if isinstance(
            field_type,
            type,
        ) and issubclass(
            field_type,
            ModelAutoSchema,
        ):
            model_attribute: models.ModelAttribute = getattr(
                model,
                field,
            )
            field_type_generated = field_type.get_schema()
            if isinstance(model_attribute, property):
                return cls._generate_property_custom_field(
                    field_type_generated=field_type_generated,
                    model=model,
                    field=field,
                    model_attribute=model_attribute,
                    extra_field_config=extra_field_config,
                )
            if model_attribute.property.uselist:
                field_type_generated = list[field_type_generated]  # type: ignore
            is_nullable = next(
                iter(model_attribute.property.local_columns),
            ).nullable
            return (
                (
                    field_type_generated | None
                    if is_nullable
                    else field_type_generated
                ),
                pydantic_core.PydanticUndefined,
            )
        return field_type, pydantic_core.PydanticUndefined

    @classmethod
    def _get_db_types_mapping(
        cls,
    ) -> dict[
        type[typing.Any],
        collections.abc.Callable[
            [
                models.SQLAlchemyModel,
                str,
                models.ModelAttribute,
                models.ModelType,
                MetaExtraFieldConfig,
            ],
            PydanticFieldConfig,
        ],
    ]:
        """Get mapping of types and field generators."""
        return {
            sqlalchemy.String: cls._generate_string_field,
            sqlalchemy.Text: cls._generate_string_field,
            sqlalchemy.Integer: cls._generate_integer_field,
            sqlalchemy.SmallInteger: cls._generate_small_integer_field,
            sqlalchemy.Enum: cls._generate_enum_field,
            sqlalchemy.Date: cls._generate_date_field,
            sqlalchemy.DateTime: cls._generate_datetime_field,
            sqlalchemy.Boolean: cls._generate_bool_field,
            sqlalchemy.Numeric: cls._generate_numeric_field,
            sqlalchemy.Interval: cls._generate_interval_field,
            sqlalchemy.ARRAY: cls._generate_array_field,
            sqlalchemy.dialects.postgresql.JSON: cls._generate_postgres_json_field,  # noqa: E501
            sqlalchemy.dialects.postgresql.ranges.DATERANGE: cls._generate_date_range,  # noqa: E501
        }

    @classmethod
    def _generate_property_field(
        cls,
        model: models.SQLAlchemyModel,
        field: str,
        model_attribute: property,
        extra_field_config: MetaExtraFieldConfig,
    ) -> PydanticFieldConfig:
        """Generate property field."""
        return (
            model_attribute.fget.__annotations__["return"],
            pydantic_core.PydanticUndefined,
        )

    @classmethod
    def _generate_property_custom_field(
        cls,
        field_type_generated: type,
        model: models.SQLAlchemyModel,
        field: str,
        model_attribute: property,
        extra_field_config: MetaExtraFieldConfig,
    ) -> PydanticFieldConfig:
        """Generate property for custom field."""
        annotation = model_attribute.fget.__annotations__["return"]
        is_nullable = False
        if typing.get_origin(annotation) == types.UnionType:
            annotation, _ = typing.get_args(annotation)
            is_nullable = True
        if isinstance(annotation, collections.abc.Iterable):
            field_type_generated = list[field_type_generated]  # type: ignore
        return (
            (
                field_type_generated | None
                if is_nullable
                else field_type_generated
            ),
            pydantic_core.PydanticUndefined,
        )

    @classmethod
    def _generate_string_field(
        cls,
        model: models.SQLAlchemyModel,
        field: str,
        model_attribute: models.ModelAttribute,
        model_type: models.ModelType,
        extra_field_config: MetaExtraFieldConfig,
    ) -> PydanticFieldConfig:
        """Generate string field."""
        constraints: dict[str, typing.Any] = {
            "strip_whitespace": True,
            "max_length": model_type.length,  # type: ignore
        }
        constraints.update(**extra_field_config)
        return (  # type: ignore
            typing.Annotated[
                str | None if model_attribute.nullable else str,
                pydantic.StringConstraints(**constraints),
            ],
            pydantic_core.PydanticUndefined,
        )

    @classmethod
    def _generate_integer_field(
        cls,
        model: models.SQLAlchemyModel,
        field: str,
        model_attribute: models.ModelAttribute,
        model_type: models.ModelType,
        extra_field_config: MetaExtraFieldConfig,
    ) -> PydanticFieldConfig:
        """Generate integer field."""
        constraints: dict[str, typing.Any] = {
            "ge": -2147483648,
            "le": 2147483647,
        }
        constraints.update(**extra_field_config)
        int_type = typing.Annotated[int, pydantic.Field(**constraints)]
        return (
            int_type | None if model_attribute.nullable else int_type,
            pydantic_core.PydanticUndefined,
        )

    @classmethod
    def _generate_small_integer_field(
        cls,
        model: models.SQLAlchemyModel,
        field: str,
        model_attribute: models.ModelAttribute,
        model_type: models.ModelType,
        extra_field_config: MetaExtraFieldConfig,
    ) -> PydanticFieldConfig:
        """Generate small integer field."""
        constraints: MetaExtraFieldConfig = {
            "ge": -32768,
            "le": 32767,
        }
        constraints.update(**extra_field_config)
        int_type = typing.Annotated[int, pydantic.Field(**constraints)]
        return (
            int_type | None if model_attribute.nullable else int_type,
            pydantic_core.PydanticUndefined,
        )

    @classmethod
    def _generate_numeric_field(
        cls,
        model: models.SQLAlchemyModel,
        field: str,
        model_attribute: models.ModelAttribute,
        model_type: models.ModelType,
        extra_field_config: MetaExtraFieldConfig,
    ) -> PydanticFieldConfig:
        """Generate numeric field."""
        constraints: MetaExtraFieldConfig = {**extra_field_config}
        decimal_type = typing.Annotated[
            decimal.Decimal,
            pydantic.Field(
                json_schema_extra={
                    "precision": model_type.precision,  # type: ignore
                    "scale": model_type.scale,  # type: ignore
                },
                **constraints,
            ),
        ]
        return (
            decimal_type | None if model_attribute.nullable else decimal_type,
            pydantic_core.PydanticUndefined,
        )

    @classmethod
    def _generate_bool_field(
        cls,
        model: models.SQLAlchemyModel,
        field: str,
        model_attribute: models.ModelAttribute,
        model_type: models.ModelType,
        extra_field_config: MetaExtraFieldConfig,
    ) -> PydanticFieldConfig:
        """Generate boolean field."""
        return (
            bool | None if model_attribute.nullable else bool,
            pydantic_core.PydanticUndefined,
        )

    @classmethod
    def _generate_enum_field(
        cls,
        model: models.SQLAlchemyModel,
        field: str,
        model_attribute: models.ModelAttribute,
        model_type: models.ModelType,
        extra_field_config: MetaExtraFieldConfig,
    ) -> PydanticFieldConfig:
        """Generate enum field."""
        if model_type.enum_class is None:  # type: ignore
            raise UnableToExtractEnumClassError(  # pragma: no cover
                f"Can't extract enum for {field} in {model}",
            )
        return (
            model_type.enum_class | None  # type: ignore
            if model_attribute.nullable
            else model_type.enum_class  # type: ignore
        ), pydantic_core.PydanticUndefined

    @classmethod
    def _generate_datetime_field(
        cls,
        model: models.SQLAlchemyModel,
        field: str,
        model_attribute: models.ModelAttribute,
        model_type: models.ModelType,
        extra_field_config: dict[str, typing.Any],
    ) -> PydanticFieldConfig:
        """Generate datetime field."""
        return (
            datetime.datetime | None
            if model_attribute.nullable
            else datetime.datetime
        ), pydantic_core.PydanticUndefined

    @classmethod
    def _generate_date_field(
        cls,
        model: models.SQLAlchemyModel,
        field: str,
        model_attribute: models.ModelAttribute,
        model_type: models.ModelType,
        extra_field_config: MetaExtraFieldConfig,
    ) -> PydanticFieldConfig:
        """Generate date field."""
        return (
            datetime.date | None if model_attribute.nullable else datetime.date
        ), pydantic_core.PydanticUndefined

    @classmethod
    def _generate_interval_field(
        cls,
        model: models.SQLAlchemyModel,
        field: str,
        model_attribute: models.ModelAttribute,
        model_type: models.ModelType,
        extra_field_config: MetaExtraFieldConfig,
    ) -> PydanticFieldConfig:
        """Generate interval field."""
        return (
            datetime.timedelta | None
            if model_attribute.nullable
            else datetime.timedelta
        ), pydantic_core.PydanticUndefined

    @classmethod
    def _generate_array_field(
        cls,
        model: models.SQLAlchemyModel,
        field: str,
        model_attribute: models.ModelAttribute,
        model_type: models.ModelType,
        extra_field_config: MetaExtraFieldConfig,
    ) -> PydanticFieldConfig:
        """Generate array field."""
        list_type, _ = cls._get_db_types_mapping()[
            model_type.item_type.__class__  # type: ignore
        ](
            model,
            field,
            model_attribute,
            model_type.item_type,  # type: ignore
            extra_field_config,
        )
        return (
            list[list_type] | None  # type: ignore
            if model_attribute.nullable
            else list[list_type]  # type: ignore
        ), pydantic_core.PydanticUndefined

    @classmethod
    def _generate_postgres_json_field(
        cls,
        model: models.SQLAlchemyModel,
        field: str,
        model_attribute: models.ModelAttribute,
        model_type: models.ModelType,
        extra_field_config: MetaExtraFieldConfig,
    ) -> PydanticFieldConfig:
        """Generate postgres json field."""
        return (
            dict[str, str | int | float] | None
            if model_attribute.nullable
            else dict[str, str | int | float]
        ), pydantic_core.PydanticUndefined

    @classmethod
    def _generate_date_range(
        cls,
        model: models.SQLAlchemyModel,
        field: str,
        model_attribute: models.ModelAttribute,
        model_type: models.ModelType,
        extra_field_config: MetaExtraFieldConfig,
    ) -> PydanticFieldConfig:
        """Generate date range field."""
        return (
            fields.PostgresRange[datetime.date] | None
            if model_attribute.nullable
            else fields.PostgresRange[datetime.date]
        ), pydantic_core.PydanticUndefined


ModelAutoSchemaT = typing.TypeVar(
    "ModelAutoSchemaT",
    bound=ModelAutoSchema,
)
