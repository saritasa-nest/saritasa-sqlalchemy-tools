import collections.abc
import typing

import sqlalchemy.orm
import sqlalchemy.sql.elements
import sqlalchemy.sql.roles

ColumnTypeT = typing.TypeVar("ColumnTypeT", bound=typing.Any)
ColumnField = (
    sqlalchemy.sql.roles.TypedColumnsClauseRole[ColumnTypeT]
    | sqlalchemy.sql.roles.ColumnsClauseRole
)

# For some reason mypy demands that orm.QueryableAttribute has two generic args
Annotation: typing.TypeAlias = (
    sqlalchemy.orm.QueryableAttribute[typing.Any]  # type: ignore
    | tuple[
        sqlalchemy.orm.QueryableAttribute[typing.Any],
        sqlalchemy.ScalarSelect[typing.Any],
    ]
)
AnnotationSequence: typing.TypeAlias = collections.abc.Sequence[Annotation]

ComparisonOperator: typing.TypeAlias = collections.abc.Callable[
    [sqlalchemy.orm.InstrumentedAttribute[typing.Any], typing.Any],
    sqlalchemy.ColumnExpressionArgument[bool],
]
LazyLoaded: typing.TypeAlias = (
    sqlalchemy.orm.InstrumentedAttribute[typing.Any]
    | collections.abc.Sequence[
        sqlalchemy.orm.InstrumentedAttribute[typing.Any]
    ]
)
LazyLoadedSequence: typing.TypeAlias = collections.abc.Sequence[LazyLoaded]
SubQueryReturnT = typing.TypeVar(
    "SubQueryReturnT",
    bound=typing.Any,
)
