import collections.abc
import enum
import typing

import sqlalchemy

from . import core

BaseModelT = typing.TypeVar(
    "BaseModelT",
    bound="core.BaseModel",
)
BaseSoftDeleteModelT = typing.TypeVar(
    "BaseSoftDeleteModelT",
    bound="core.BaseSoftDeleteModel",
)
FieldEnumT = typing.TypeVar(
    "FieldEnumT",
    bound="enum.Enum",
)
SQLAlchemyModel: typing.TypeAlias = sqlalchemy.orm.DeclarativeBase
SelectStatement: typing.TypeAlias = sqlalchemy.Select[tuple[BaseModelT]]
# For some reason mypy demands that orm.InstrumentedAttribute has two generic
# args
ModelAttribute: typing.TypeAlias = sqlalchemy.orm.InstrumentedAttribute[  # type: ignore
    typing.Any
]
ModelAttributeSequence: typing.TypeAlias = collections.abc.Sequence[
    ModelAttribute
]
ModelType: typing.TypeAlias = sqlalchemy.sql.type_api.TypeEngine[typing.Any]  # type: ignore
