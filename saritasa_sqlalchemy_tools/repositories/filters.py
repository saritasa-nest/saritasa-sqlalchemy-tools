import collections.abc
import dataclasses
import datetime
import typing

import sqlalchemy
import sqlalchemy.dialects.postgresql
import sqlalchemy.orm

from .. import metrics, models

SQLWhereFilter = sqlalchemy.ColumnExpressionArgument[bool]
WhereFilter = typing.Union[SQLWhereFilter, "Filter"]
WhereFilters = collections.abc.Sequence[WhereFilter]
_FilterType: typing.TypeAlias = (
    str
    | int
    | bool
    | list[str]
    | list[int]
    | list[models.FieldEnumT]
    | list[None]
    | sqlalchemy.dialects.postgresql.Range[typing.Any]
    | datetime.date
    | datetime.datetime
    | collections.abc.Sequence[str]
    | collections.abc.Sequence[int]
    | collections.abc.Sequence[models.FieldEnumT]
    | collections.abc.Sequence[None]
    | collections.abc.Sequence[datetime.date]
    | collections.abc.Sequence[datetime.datetime]
    | None
)
FilterType: typing.TypeAlias = _FilterType[typing.Any]


@dataclasses.dataclass
class Filter:
    """Define filter value."""

    field: str
    value: FilterType
    exclude: bool = False

    @metrics.tracker
    def transform_filter(
        self,
        model: type[models.BaseModelT],
    ) -> SQLWhereFilter:
        """Transform filter valid for sqlalchemy."""
        field_name, *filter_arg = self.field.split("__")
        filter_object: SQLWhereFilter
        if isinstance(
            getattr(model, field_name).property,
            sqlalchemy.orm.Relationship,
        ):
            filter_object = self.transform_relationship(
                field_name=field_name,
                filter_arg=filter_arg,
                model=model,
                value=self.value,
            )
        elif len(filter_arg) > 1:
            raise ValueError(
                "Long filter args only supported for relationships!",
            )
        else:
            filter_object = self.transform_simple_filter(
                field_name=field_name,
                filter_arg=filter_arg[0],
                model=model,
                value=self.value,
            )
        if self.exclude:
            return sqlalchemy.not_(filter_object)
        return filter_object

    def transform_relationship(
        self,
        field_name: str,
        filter_arg: collections.abc.Sequence[str],
        model: type[models.BaseModelT],
        value: FilterType,
    ) -> SQLWhereFilter:
        """Prepare relationship filter."""
        field: models.ModelAttribute = getattr(model, field_name)
        property_filter = field.any if field.property.uselist else field.has
        return property_filter(
            self.__class__(
                field="__".join(filter_arg),
                value=value,
            ).transform_filter(
                model=field.property.mapper.class_,
            ),
        )

    @metrics.tracker
    def transform_simple_filter(
        self,
        field_name: str,
        filter_arg: str,
        model: type[models.BaseModelT],
        value: FilterType,
    ) -> SQLWhereFilter:
        """Transform simple filter for sqlalchemy."""
        filter_args_mapping = {
            "is": "is_",
            "in": "in_",
            "overlaps": "overlaps",
            "exact": "__eq__",
            "gt": "__gt__",
            "gte": "__ge__",
            "lt": "__lt__",
            "lte": "__le__",
        }
        field: sqlalchemy.orm.attributes.InstrumentedAttribute[typing.Any] = (
            getattr(
                model,
                field_name,
            )
        )
        filter_operator = getattr(field, filter_args_mapping[filter_arg])(
            value,
        )
        return filter_operator


@metrics.tracker
def transform_search_filter(
    model: type[models.BaseModelT],
    search_fields: collections.abc.Sequence[str],
    value: FilterType,
) -> SQLWhereFilter:
    """Prepare search filter sql alchemy."""
    search_filters = [
        sqlalchemy.cast(getattr(model, field), sqlalchemy.String).ilike(
            f"%{str(value).strip()}%",
        )
        for field in search_fields
        if value
    ]
    return sqlalchemy.or_(*search_filters)
