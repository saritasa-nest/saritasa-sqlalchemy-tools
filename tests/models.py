import datetime
import decimal
import enum
import typing

import sqlalchemy.dialects.postgresql
import sqlalchemy.orm

import saritasa_sqlalchemy_tools


class RelatedModel(
    saritasa_sqlalchemy_tools.TimeStampedBaseIDModel,
):
    """Test models for checking relationships."""

    __tablename__ = "related_model"

    test_model_list = sqlalchemy.orm.relationship(
        "TestModel",
        foreign_keys="TestModel.related_model_id",
        back_populates="related_model",
    )

    test_model_list_nullable = sqlalchemy.orm.relationship(
        "TestModel",
        foreign_keys="TestModel.related_model_id_nullable",
        back_populates="related_model_nullable",
    )

    test_model_id: sqlalchemy.orm.Mapped[int | None] = (
        sqlalchemy.orm.mapped_column(
            sqlalchemy.ForeignKey(
                "test_model.id",
                ondelete="CASCADE",
                use_alter=True,
            ),
            nullable=True,
        )
    )

    test_model = sqlalchemy.orm.relationship(
        "TestModel",
        foreign_keys=[test_model_id],
        back_populates="related_models",
    )

    m2m_test_model_list = sqlalchemy.orm.relationship(
        "TestModel",
        secondary="m2m_model",
        uselist=True,
        viewonly=True,
    )

    m2m_associations = sqlalchemy.orm.relationship(
        "M2MModel",
        back_populates="related_model",
        foreign_keys="M2MModel.related_model_id",
        cascade="all, delete",
        uselist=True,
    )


class FieldsMixin:
    """Mixin which adds fields to models."""

    text: sqlalchemy.orm.Mapped[str] = sqlalchemy.orm.mapped_column(
        sqlalchemy.String(250),
        nullable=False,
    )

    text_nullable: sqlalchemy.orm.Mapped[str | None] = (
        sqlalchemy.orm.mapped_column(
            sqlalchemy.String(30),
            nullable=True,
        )
    )

    class TextEnum(enum.StrEnum):
        value_1 = "value1"
        value_2 = "value2"
        value_3 = "value3"

    text_enum: sqlalchemy.orm.Mapped[TextEnum] = sqlalchemy.orm.mapped_column(
        sqlalchemy.Enum(TextEnum),
        nullable=False,
    )

    text_enum_nullable: sqlalchemy.orm.Mapped[TextEnum | None] = (
        sqlalchemy.orm.mapped_column(
            sqlalchemy.Enum(TextEnum),
            nullable=True,
        )
    )

    number: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(
        sqlalchemy.Integer(),
        nullable=False,
    )

    number_nullable: sqlalchemy.orm.Mapped[int | None] = (
        sqlalchemy.orm.mapped_column(
            sqlalchemy.Integer(),
            nullable=True,
        )
    )

    small_number: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(
        sqlalchemy.SmallInteger(),
        nullable=False,
    )

    small_number_nullable: sqlalchemy.orm.Mapped[int | None] = (
        sqlalchemy.orm.mapped_column(
            sqlalchemy.SmallInteger(),
            nullable=True,
        )
    )

    decimal_number: sqlalchemy.orm.Mapped[decimal.Decimal] = (
        sqlalchemy.orm.mapped_column(
            sqlalchemy.Numeric(),
            nullable=False,
        )
    )

    decimal_number_nullable: sqlalchemy.orm.Mapped[decimal.Decimal | None] = (
        sqlalchemy.orm.mapped_column(
            sqlalchemy.Numeric(),
            nullable=True,
        )
    )

    boolean: sqlalchemy.orm.Mapped[bool] = sqlalchemy.orm.mapped_column(
        sqlalchemy.Boolean(),
        nullable=False,
    )

    boolean_nullable: sqlalchemy.orm.Mapped[bool | None] = (
        sqlalchemy.orm.mapped_column(
            sqlalchemy.Boolean(),
            nullable=True,
        )
    )

    text_list: sqlalchemy.orm.Mapped[list[str]] = sqlalchemy.orm.mapped_column(
        sqlalchemy.ARRAY(sqlalchemy.String),
        nullable=False,
    )

    text_list_nullable: sqlalchemy.orm.Mapped[list[str] | None] = (
        sqlalchemy.orm.mapped_column(
            sqlalchemy.ARRAY(sqlalchemy.String),
            nullable=True,
        )
    )

    date_time: sqlalchemy.orm.Mapped[datetime.datetime] = (
        sqlalchemy.orm.mapped_column(
            sqlalchemy.DateTime(),
            nullable=False,
        )
    )

    date_time_nullable: sqlalchemy.orm.Mapped[datetime.datetime | None] = (
        sqlalchemy.orm.mapped_column(
            sqlalchemy.DateTime(),
            nullable=True,
        )
    )

    date: sqlalchemy.orm.Mapped[datetime.date] = sqlalchemy.orm.mapped_column(
        sqlalchemy.Date(),
        nullable=False,
    )

    date_nullable: sqlalchemy.orm.Mapped[datetime.date | None] = (
        sqlalchemy.orm.mapped_column(
            sqlalchemy.Date(),
            nullable=True,
        )
    )

    timedelta: sqlalchemy.orm.Mapped[datetime.timedelta] = (
        sqlalchemy.orm.mapped_column(
            sqlalchemy.Interval(),
            nullable=False,
        )
    )

    timedelta_nullable: sqlalchemy.orm.Mapped[datetime.timedelta | None] = (
        sqlalchemy.orm.mapped_column(
            sqlalchemy.Interval(),
            nullable=True,
        )
    )

    json_field: sqlalchemy.orm.Mapped[dict[str, str | int | float]] = (
        sqlalchemy.orm.mapped_column(
            sqlalchemy.dialects.postgresql.JSON(),
            nullable=False,
        )
    )

    json_field_nullable: sqlalchemy.orm.Mapped[
        dict[str, str | int | float]
    ] = sqlalchemy.orm.mapped_column(
        sqlalchemy.dialects.postgresql.JSON(),
        nullable=True,
    )

    @property
    def custom_property(self) -> str:
        """Implement property."""
        return ""

    @property
    def custom_property_nullable(self) -> str | None:
        """Implement property."""
        return ""


class TestModel(
    FieldsMixin,
    saritasa_sqlalchemy_tools.TimeStampedBaseIDModel,
):
    """Test model for testing."""

    __tablename__ = "test_model"

    m2m_filters: typing.ClassVar = {
        "m2m_related_model_id": saritasa_sqlalchemy_tools.M2MFilterConfig(
            relation_field="m2m_associations",
            filter_field="related_model_id",
            match_field="test_model_id",
        ),
    }

    related_model_id: sqlalchemy.orm.Mapped[int] = (
        sqlalchemy.orm.mapped_column(
            sqlalchemy.ForeignKey(
                "related_model.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        )
    )

    related_model = sqlalchemy.orm.relationship(
        "RelatedModel",
        foreign_keys=[related_model_id],
        back_populates="test_model_list",
    )

    related_model_id_nullable: sqlalchemy.orm.Mapped[int | None] = (
        sqlalchemy.orm.mapped_column(
            sqlalchemy.ForeignKey(
                "related_model.id",
                ondelete="CASCADE",
            ),
            nullable=True,
        )
    )

    related_model_nullable = sqlalchemy.orm.relationship(
        "RelatedModel",
        foreign_keys=[related_model_id_nullable],
        back_populates="test_model_list_nullable",
    )

    related_models = sqlalchemy.orm.relationship(
        "RelatedModel",
        foreign_keys="RelatedModel.test_model_id",
        back_populates="test_model",
    )

    related_models_count: sqlalchemy.orm.Mapped[int | None] = (
        sqlalchemy.orm.column_property(
            sqlalchemy.select(sqlalchemy.func.count(RelatedModel.id))
            .correlate_except(RelatedModel)
            .scalar_subquery(),
            deferred=True,
        )
    )

    related_models_count_query: sqlalchemy.orm.Mapped[int | None] = (
        sqlalchemy.orm.query_expression()
    )

    m2m_related_models = sqlalchemy.orm.relationship(
        "RelatedModel",
        secondary="m2m_model",
        uselist=True,
        viewonly=True,
    )

    m2m_associations = sqlalchemy.orm.relationship(
        "M2MModel",
        back_populates="test_model",
        foreign_keys="M2MModel.test_model_id",
        cascade="all, delete",
        uselist=True,
    )

    def __repr__(self) -> str:
        """Get str representation."""
        return f"TestModel<{self.id}>"

    @property
    def custom_property_related_model(self) -> typing.Any:
        """Implement property."""
        return self.related_model

    @property
    def custom_property_related_model_nullable(self) -> typing.Any | None:
        """Implement property."""
        return self.related_model_nullable

    @property
    def custom_property_related_models(self) -> list[typing.Any]:
        """Implement property."""
        return self.related_models


class SoftDeleteTestModel(
    FieldsMixin,
    saritasa_sqlalchemy_tools.SoftDeleteBaseIDModel,
):
    """Test model for testing(soft-delete case)."""

    __tablename__ = "soft_delete_test_model"


class M2MModel(saritasa_sqlalchemy_tools.TimeStampedBaseIDModel):
    """Test model for testing m2m features."""

    __tablename__ = "m2m_model"

    test_model_id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(
        sqlalchemy.ForeignKey(
            "test_model.id",
            ondelete="CASCADE",
        ),
        nullable=False,
    )

    test_model = sqlalchemy.orm.relationship(
        "TestModel",
        foreign_keys=[test_model_id],
        back_populates="m2m_associations",
    )

    related_model_id: sqlalchemy.orm.Mapped[int] = (
        sqlalchemy.orm.mapped_column(
            sqlalchemy.ForeignKey(
                "related_model.id",
                ondelete="CASCADE",
            ),
            nullable=False,
        )
    )

    related_model = sqlalchemy.orm.relationship(
        "RelatedModel",
        foreign_keys=[related_model_id],
        back_populates="m2m_associations",
    )
