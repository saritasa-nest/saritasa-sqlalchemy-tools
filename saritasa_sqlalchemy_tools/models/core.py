import contextlib
import datetime
import typing

import sqlalchemy
import sqlalchemy.ext.asyncio
import sqlalchemy.orm

from .. import metrics


class TimeStampedMixin:
    """A mixin that adds timestamped fields to the model."""

    created: sqlalchemy.orm.Mapped[datetime.datetime] = (
        sqlalchemy.orm.mapped_column(
            nullable=False,
            server_default=sqlalchemy.sql.func.now(),
        )
    )
    modified: sqlalchemy.orm.Mapped[datetime.datetime] = (
        sqlalchemy.orm.mapped_column(
            nullable=False,
            server_default=sqlalchemy.sql.func.now(),
            onupdate=sqlalchemy.sql.func.now(),
        )
    )


class SoftDeleteMixin:
    """A mixin which supports soft delete."""

    deleted: sqlalchemy.orm.Mapped[datetime.datetime | None] = (
        sqlalchemy.orm.mapped_column(
            nullable=True,
        )
    )


class IDMixin:
    """A mixin which adds id field to model."""

    pk_field: str = "id"
    id: sqlalchemy.orm.Mapped[int] = sqlalchemy.orm.mapped_column(
        primary_key=True,
    )


class BaseModel(
    sqlalchemy.ext.asyncio.AsyncAttrs,
    sqlalchemy.orm.DeclarativeBase,
):
    """Base model class."""

    __abstract__ = True
    pk_field: str

    @property
    @metrics.tracker
    def as_dict(self) -> dict[str, typing.Any]:
        """Convert model to dict."""
        data = {}
        for column in self.__table__.columns:
            if column_name := column.name:
                with contextlib.suppress(sqlalchemy.exc.MissingGreenlet):
                    data[column_name] = getattr(self, column_name)
        return data

    @property
    def pk(self) -> typing.Any:
        """Get primary key value."""
        return getattr(self, self.pk_field)


class BaseIDModel(IDMixin, BaseModel):
    """Base model with id."""

    __abstract__ = True


class BaseTimeStampedModel(TimeStampedMixin, BaseModel):
    """Base model with timestamps."""

    __abstract__ = True


class BaseSoftDeleteModel(SoftDeleteMixin, BaseTimeStampedModel):
    """Base model with support for soft deletion."""

    __abstract__ = True


class TimeStampedBaseIDModel(BaseIDModel, BaseTimeStampedModel):
    """Base id model with timestamp fields."""

    __abstract__ = True


class SoftDeleteBaseIDModel(BaseIDModel, BaseSoftDeleteModel):
    """Base id model with timestamp fields and support for soft-delete."""

    __abstract__ = True
