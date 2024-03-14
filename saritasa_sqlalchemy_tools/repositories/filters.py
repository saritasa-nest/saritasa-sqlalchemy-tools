import collections.abc
import dataclasses
import datetime
import typing

import sqlalchemy
import sqlalchemy.dialects.postgresql
import sqlalchemy.orm

from .. import models

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

    api_filter: str
    value: FilterType

    def transform_filter(
        self,
        model: type[models.BaseModelT],
    ) -> SQLWhereFilter:
        """Transform filter valid for sqlalchemy."""
        field_name, filter_arg = self.api_filter.split("__")
        if field_name in model.m2m_filters:
            return self.transform_m2m_filter(
                field_name=field_name,
                filter_arg=filter_arg,
                model=model,
                value=self.value,
            )
        return self.transform_simple_filter(
            field_name=field_name,
            filter_arg=filter_arg,
            model=model,
            value=self.value,
        )

    def transform_m2m_filter(
        self,
        field_name: str,
        filter_arg: str,
        model: type[models.BaseModelT],
        value: FilterType,
    ) -> SQLWhereFilter:
        """Transform m2m filter for sqlalchemy."""
        m2m_config = model.m2m_filters[field_name]
        m2m_model = getattr(model, m2m_config.relation_field).mapper.class_
        return sqlalchemy.and_(
            self.transform_simple_filter(
                m2m_config.filter_field,
                filter_arg,
                model=m2m_model,
                value=value,
            ),
            getattr(
                m2m_model,
                m2m_config.match_field,
            )
            == getattr(
                model,
                model.pk_field,
            ),
        )

    def transform_simple_filter(
        self,
        field_name: str,
        filter_arg: str,
        model: type[models.BaseModelT],
        value: FilterType,
    ) -> SQLWhereFilter:
        """Transform simple filter for sqlalchemy."""
        filter_args_mapping = {
            "exact": "is_",
            "in": "in_",
            "overlaps": "overlaps",
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
        if (
            filter_arg
            in (
                "gt",
                "gte",
                "lt",
                "lte",
            )
            and field.nullable
        ):
            filter_operator = sqlalchemy.or_(
                filter_operator,
                field.is_(None),
            )
        return filter_operator


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
