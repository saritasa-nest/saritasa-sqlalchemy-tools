import collections.abc
import enum
import typing

import sqlalchemy

try:
    from ..schema import OpenAPIDocsEnumMixin  # type: ignore
except ImportError:  # pragma: no cover

    class OpenAPIDocsEnumMixin:  # type:ignore
        """Placeholder."""


class OrderingEnumMeta(enum.EnumMeta):
    """Meta class for ordering enum."""

    def __new__(  # noqa: ANN204
        metacls,  # noqa: N804
        cls,  # noqa: ANN001
        bases,  # noqa: ANN001
        classdict,  # noqa: ANN001
        **kwds,
    ):
        """Extend enum with descending fields."""
        for name in list(classdict._member_names):
            classdict[f"{name}_desc"] = f"-{classdict[name]}"
        return super().__new__(metacls, cls, bases, classdict, **kwds)


class OrderingEnum(
    OpenAPIDocsEnumMixin,
    enum.StrEnum,
    metaclass=OrderingEnumMeta,
):
    """Representation of ordering fields."""

    @property
    def sql_clause(self) -> "SQLOrderingClause":
        """Convert ordering value to sqlalchemy ordering clause."""
        if self.startswith("-"):
            return sqlalchemy.desc(self[1:])
        return self


SQLOrderingClause = str | sqlalchemy.ColumnExpressionArgument[typing.Any]
OrderingClause = SQLOrderingClause | OrderingEnum
OrderingClauses: typing.TypeAlias = collections.abc.Sequence[OrderingClause]
