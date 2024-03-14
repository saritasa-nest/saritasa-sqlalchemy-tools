import collections.abc
import enum
import typing

import sqlalchemy


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


class OrderingEnum(enum.StrEnum, metaclass=OrderingEnumMeta):
    """Representation of ordering fields."""

    @property
    def db_clause(self) -> str | sqlalchemy.ColumnExpressionArgument[str]:
        """Convert ordering value to sqlalchemy ordering clause."""
        if self.startswith("-"):
            return sqlalchemy.desc(self[1:])
        return self


OrderingClausesT: typing.TypeAlias = collections.abc.Sequence[
    str | sqlalchemy.ColumnExpressionArgument[str] | OrderingEnum
]
