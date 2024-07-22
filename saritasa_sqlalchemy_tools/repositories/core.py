import abc
import collections.abc
import datetime
import typing

import sqlalchemy
import sqlalchemy.ext.asyncio
import sqlalchemy.orm

from .. import metrics, models
from . import filters, ordering, types

BaseRepositoryT = typing.TypeVar(
    "BaseRepositoryT",
    bound="BaseRepository[typing.Any]",
)


class BaseRepository(
    typing.Generic[models.BaseModelT],
    metaclass=abc.ABCMeta,
):
    """Abstract class for repositories.

    Repository provide the interface for interaction with DB table.

    """

    model: type[models.BaseModelT]
    # Sequence of field names that should be excluded during bulk creating
    default_exclude_bulk_create_fields: collections.abc.Sequence[str] = ()
    # Sequence of field names that should be excluded during bulk updating
    default_exclude_bulk_update_fields: collections.abc.Sequence[str] = ()

    def __init__(
        self,
        db_session: sqlalchemy.ext.asyncio.AsyncSession,
    ) -> None:
        self.db_session = db_session

    @metrics.tracker
    def init_other(
        self,
        repository_class: type[BaseRepositoryT],
    ) -> BaseRepositoryT:
        """Init other repo from current."""
        return repository_class(db_session=self.db_session)

    @metrics.tracker
    async def flush(self) -> None:
        """Perform changes to database."""
        await self.db_session.flush()

    @metrics.tracker
    async def refresh(
        self,
        instance: models.BaseModelT,
        attribute_names: collections.abc.Sequence[str] | None = None,
    ) -> None:
        """Refresh instance."""
        await self.db_session.refresh(
            instance=instance,
            attribute_names=attribute_names,
        )

    @metrics.tracker
    def expire(self, instance: models.BaseModelT) -> None:
        """Expire instance.

        This mark instance as expired, which means all it's attrs need to be
        fetched from db again.

        """
        self.db_session.expire(instance)

    @metrics.tracker
    async def save(
        self,
        instance: models.BaseModelT,
        refresh: bool = False,
        attribute_names: collections.abc.Sequence[str] | None = None,
    ) -> models.BaseModelT:
        """Save model instance into db."""
        self.db_session.add(instance=instance)
        await self.flush()
        if refresh:
            await self.refresh(instance, attribute_names)
        return instance

    @metrics.tracker
    async def delete(self, instance: models.BaseModelT) -> None:
        """Delete model instance into db."""
        await self.db_session.delete(instance=instance)
        await self.flush()

    @metrics.tracker
    async def delete_batch(
        self,
        where: filters.WhereFilters = (),
        **filters_by: typing.Any,
    ) -> None:
        """Delete batch of objects from db."""
        await self.db_session.execute(
            statement=(
                sqlalchemy.sql.delete(self.model)
                .where(*self.process_where_filters(*where))
                .filter_by(**filters_by)
            ),
        )

    @metrics.tracker
    def model_as_dict(
        self,
        instance: models.BaseModelT,
        exclude_fields: collections.abc.Sequence[str] = (),
    ) -> dict[str, typing.Any]:
        """Convert model to dict except fields from `exclude_fields`."""
        return {
            column_name: value
            for column_name, value in instance.as_dict.items()
            if column_name not in exclude_fields
        }

    @metrics.tracker
    def objects_as_dict(
        self,
        objects: collections.abc.Sequence[models.BaseModelT],
        exclude_fields: collections.abc.Sequence[str] = (),
    ) -> list[dict[str, typing.Any]]:
        """Convert objects to list of dicts with field values."""
        return [
            self.model_as_dict(
                instance=obj,
                exclude_fields=exclude_fields,
            )
            for obj in objects
        ]

    @metrics.tracker
    async def insert_batch(
        self,
        objects: collections.abc.Sequence[models.BaseModelT],
        exclude_fields: collections.abc.Sequence[str] = (),
    ) -> list[models.BaseModelT]:
        """Create batch of objects in db."""
        if not objects:  # pragma: no cover
            return []

        objects_as_dict = self.objects_as_dict(
            objects=objects,
            exclude_fields=(
                exclude_fields or self.default_exclude_bulk_create_fields
            ),
        )
        created_objects = await self.db_session.scalars(
            sqlalchemy.sql.insert(self.model)
            .returning(self.model)
            .values(objects_as_dict),
        )
        await self.flush()
        return list(created_objects.all())

    @metrics.tracker
    async def update_batch(
        self,
        objects: collections.abc.Sequence[models.BaseModelT],
        exclude_fields: collections.abc.Sequence[str] = (),
    ) -> None:
        """Update batch of objects in db."""
        if not objects:  # pragma: no cover
            return

        objects_as_dict = self.objects_as_dict(
            objects=objects,
            exclude_fields=(
                exclude_fields or self.default_exclude_bulk_update_fields
            ),
        )
        await self.db_session.execute(
            sqlalchemy.sql.update(self.model),
            objects_as_dict,
        )
        await self.flush()

    @property
    def select_statement(self) -> models.SelectStatement[models.BaseModelT]:
        """Generate empty select statement."""
        return sqlalchemy.select(self.model)

    @metrics.tracker
    def get_annotated_statement(
        self,
        statement: models.SelectStatement[models.BaseModelT] | None = None,
        *annotations: types.Annotation,
    ) -> models.SelectStatement[models.BaseModelT]:
        """Pick annotations which should be returned."""
        if statement is not None:
            select_statement = statement
        else:
            select_statement = self.select_statement
        for annotation in annotations:
            if isinstance(annotation, tuple):
                select_statement = select_statement.options(
                    sqlalchemy.orm.with_expression(*annotation),
                )
            else:
                select_statement = select_statement.options(
                    sqlalchemy.orm.undefer(annotation),
                )
        return select_statement

    @metrics.tracker
    def get_filter_statement(
        self,
        statement: models.SelectStatement[models.BaseModelT] | None = None,
        *where: filters.WhereFilter,
        **filters_by: typing.Any,
    ) -> models.SelectStatement[models.BaseModelT]:
        """Get statement with filtering."""
        if statement is not None:
            select_statement = statement
        else:
            select_statement = self.select_statement
        processed_where_filters = self.process_where_filters(*where)
        processed_filters_by, left_out_filters_by = (
            self.process_filters_by_filters(**filters_by)
        )
        return select_statement.where(
            *processed_where_filters,
            *processed_filters_by,
        ).filter_by(**left_out_filters_by)

    @classmethod
    @metrics.tracker
    def process_where_filters(
        cls,
        *where: filters.WhereFilter,
    ) -> collections.abc.Sequence[filters.SQLWhereFilter]:
        """Process where filters."""
        processed_where_filters: list[filters.SQLWhereFilter] = []
        for where_filter in where:
            if isinstance(where_filter, filters.Filter):
                processed_where_filters.append(
                    where_filter.transform_filter(cls.model),  # type: ignore
                )
                continue
            processed_where_filters.append(where_filter)
        return processed_where_filters

    @classmethod
    @metrics.tracker
    def process_filters_by_filters(
        cls,
        **filters_by: typing.Any,
    ) -> tuple[
        collections.abc.Sequence[filters.SQLWhereFilter],
        dict[str, typing.Any],
    ]:
        """Process where filters."""
        processed_where_filters: list[filters.SQLWhereFilter] = []
        processed_filters_by: dict[str, typing.Any] = {}
        for field, value in filters_by.items():
            if "__" in field:
                processed_where_filters.append(
                    filters.Filter(
                        field=field,
                        value=value,
                    ).transform_filter(cls.model),  # type: ignore
                )
            else:
                processed_filters_by[field] = value
        return processed_where_filters, processed_filters_by

    @metrics.tracker
    def get_order_statement(
        self,
        statement: models.SelectStatement[models.BaseModelT] | None = None,
        *clauses: ordering.OrderingClause,
    ) -> models.SelectStatement[models.BaseModelT]:
        """Get statement with ordering."""
        if statement is not None:
            select_statement = statement
        else:
            select_statement = self.select_statement
        return select_statement.order_by(
            *self.process_ordering_clauses(*clauses),
        )

    @classmethod
    @metrics.tracker
    def process_ordering_clauses(
        cls,
        *clauses: ordering.OrderingClause,
    ) -> collections.abc.Sequence[ordering.SQLOrderingClause]:
        """Process ordering clauses."""
        processed_ordering_clauses: list[ordering.SQLOrderingClause] = []
        for clause in clauses:
            if isinstance(clause, ordering.OrderingEnum):
                processed_ordering_clauses.append(clause.sql_clause)
            else:
                processed_ordering_clauses.append(clause)
        return processed_ordering_clauses

    @metrics.tracker
    def get_pagination_statement(
        self,
        statement: models.SelectStatement[models.BaseModelT] | None = None,
        offset: int | None = None,
        limit: int | None = None,
    ) -> models.SelectStatement[models.BaseModelT]:
        """Get statement with pagination."""
        if statement is not None:
            select_statement = statement
        else:
            select_statement = self.select_statement
        if offset:
            select_statement = select_statement.offset(offset)
        if limit:
            select_statement = select_statement.limit(limit)
        return select_statement

    @metrics.tracker
    def get_joined_load_statement(
        self,
        statement: models.SelectStatement[models.BaseModelT] | None = None,
        *targets: types.LazyLoaded,
    ) -> models.SelectStatement[models.BaseModelT]:
        """Get statement which will load related models."""
        if statement is not None:
            select_statement = statement
        else:
            select_statement = self.select_statement
        for target in targets:
            joined_load = []
            if isinstance(target, collections.abc.Sequence):
                joined_loader = sqlalchemy.orm.joinedload(target[0])
                for sub_target in target[1:]:
                    joined_loader = joined_loader.joinedload(sub_target)
                joined_load.append(joined_loader)
            else:
                joined_load.append(sqlalchemy.orm.joinedload(target))
            select_statement = select_statement.options(
                *joined_load,
            )
        return select_statement

    @metrics.tracker
    def get_select_in_load_statement(
        self,
        statement: models.SelectStatement[models.BaseModelT] | None = None,
        *targets: types.LazyLoaded,
    ) -> models.SelectStatement[models.BaseModelT]:
        """Get statement which will load related models separately."""
        if statement is not None:
            select_statement = statement
        else:
            select_statement = self.select_statement
        for target in targets:
            select_in_load = []
            if isinstance(target, collections.abc.Sequence):
                select_loader = sqlalchemy.orm.selectinload(target[0])
                for sub_target in target[1:]:
                    select_loader = select_loader.selectinload(sub_target)
                select_in_load.append(select_loader)
            else:
                select_in_load.append(sqlalchemy.orm.selectinload(target))
            select_statement = select_statement.options(
                *select_in_load,
            )
        return select_statement

    @metrics.tracker
    def get_fetch_statement(
        self,
        statement: models.SelectStatement[models.BaseModelT] | None = None,
        offset: int | None = None,
        limit: int | None = None,
        joined_load: types.LazyLoadedSequence = (),
        select_in_load: types.LazyLoadedSequence = (),
        annotations: types.AnnotationSequence = (),
        ordering_clauses: ordering.OrderingClauses = (),
        where: filters.WhereFilters = (),
        **filters_by: typing.Any,
    ) -> models.SelectStatement[models.BaseModelT]:
        """Prepare statement for fetching."""
        fetch_statement = self.get_joined_load_statement(
            statement,
            *joined_load,
        )
        fetch_statement = self.get_select_in_load_statement(
            fetch_statement,
            *select_in_load,
        )
        fetch_statement = self.get_annotated_statement(
            fetch_statement,
            *annotations,
        )
        fetch_statement = self.get_order_statement(
            fetch_statement,
            *ordering_clauses,
        )
        fetch_statement = self.get_filter_statement(
            fetch_statement,
            *where,
            **filters_by,
        )
        fetch_statement = self.get_pagination_statement(
            fetch_statement,
            offset=offset,
            limit=limit,
        )
        return fetch_statement

    @metrics.tracker
    async def fetch(
        self,
        statement: models.SelectStatement[models.BaseModelT] | None = None,
        unique: bool = True,
        offset: int | None = None,
        limit: int | None = None,
        joined_load: types.LazyLoadedSequence = (),
        select_in_load: types.LazyLoadedSequence = (),
        annotations: types.AnnotationSequence = (),
        ordering_clauses: ordering.OrderingClauses = (),
        where: filters.WhereFilters = (),
        **filters_by: typing.Any,
    ) -> sqlalchemy.ScalarResult[models.BaseModelT]:
        """Fetch entries."""
        scalar_result = await metrics.tracker(self.db_session.scalars)(
            statement=self.get_fetch_statement(
                statement=statement,
                offset=offset,
                limit=limit,
                joined_load=joined_load,
                select_in_load=select_in_load,
                annotations=annotations,
                ordering_clauses=ordering_clauses,
                where=where,
                **filters_by,
            ),
        )
        if unique:
            scalar_result = scalar_result.unique()
        return scalar_result

    @metrics.tracker
    async def fetch_all(
        self,
        statement: models.SelectStatement[models.BaseModelT] | None = None,
        unique: bool = True,
        offset: int | None = None,
        limit: int | None = None,
        joined_load: types.LazyLoadedSequence = (),
        select_in_load: types.LazyLoadedSequence = (),
        annotations: types.AnnotationSequence = (),
        ordering_clauses: ordering.OrderingClauses = (),
        where: filters.WhereFilters = (),
        **filters_by: typing.Any,
    ) -> collections.abc.Sequence[models.BaseModelT]:
        """Fetch all matching entries."""
        return (
            await self.fetch(
                statement=statement,
                unique=unique,
                offset=offset,
                limit=limit,
                joined_load=joined_load,
                select_in_load=select_in_load,
                annotations=annotations,
                ordering_clauses=ordering_clauses,
                where=where,
                **filters_by,
            )
        ).all()

    @metrics.tracker
    async def fetch_first(
        self,
        statement: models.SelectStatement[models.BaseModelT] | None = None,
        unique: bool = True,
        offset: int | None = None,
        limit: int | None = None,
        joined_load: types.LazyLoadedSequence = (),
        select_in_load: types.LazyLoadedSequence = (),
        annotations: types.AnnotationSequence = (),
        ordering_clauses: ordering.OrderingClauses = (),
        where: filters.WhereFilters = (),
        **filters_by: typing.Any,
    ) -> models.BaseModelT | None:
        """Get first matching instance."""
        return (
            await self.fetch(
                statement=statement,
                unique=unique,
                offset=offset,
                limit=limit,
                joined_load=joined_load,
                select_in_load=select_in_load,
                annotations=annotations,
                ordering_clauses=ordering_clauses,
                where=where,
                **filters_by,
            )
        ).first()

    @metrics.tracker
    async def count(
        self,
        where: filters.WhereFilters = (),
        **filters_by: typing.Any,
    ) -> int:
        """Get count of entries."""
        return (
            await metrics.tracker(self.db_session.scalar)(
                sqlalchemy.select(sqlalchemy.func.count())
                .select_from(self.model)
                .where(*self.process_where_filters(*where))
                .filter_by(**filters_by),
            )
        ) or 0

    @metrics.tracker
    async def exists(
        self,
        where: filters.WhereFilters = (),
        **filters_by: typing.Any,
    ) -> bool:
        """Check existence of entries."""
        return (
            await metrics.tracker(self.db_session.scalar)(
                sqlalchemy.select(
                    sqlalchemy.sql.exists(
                        self.select_statement.where(
                            *self.process_where_filters(*where),
                        ).filter_by(
                            **filters_by,
                        ),
                    ),
                ),
            )
        ) or False

    @metrics.tracker
    async def values(
        self,
        field: types.ColumnField[types.ColumnTypeT],
        statement: models.SelectStatement[models.BaseModelT] | None = None,
        joined_load: types.LazyLoadedSequence = (),
        select_in_load: types.LazyLoadedSequence = (),
        annotations: types.AnnotationSequence = (),
        ordering_clauses: ordering.OrderingClauses = (),
        where: filters.WhereFilters = (),
        **filters_by: typing.Any,
    ) -> collections.abc.Sequence[types.ColumnTypeT]:
        """Get all values of field."""
        return (
            await metrics.tracker(self.db_session.scalars)(
                (
                    statement
                    if statement is not None
                    else self.get_fetch_statement(
                        joined_load=joined_load,
                        select_in_load=select_in_load,
                        annotations=annotations,
                        ordering_clauses=ordering_clauses,
                        where=where,
                        **filters_by,
                    )
                ).with_only_columns(field),
            )
        ).all()


class BaseSoftDeleteRepository(
    BaseRepository[models.BaseSoftDeleteModelT],
):
    """Repository for model with soft delete feature."""

    @metrics.tracker
    async def delete(
        self,
        instance: models.BaseSoftDeleteModelT,
    ) -> None:
        """Mark model as deleted model instance into db."""
        instance.deleted = datetime.datetime.now(datetime.UTC).replace(
            tzinfo=None,
        )
        await self.save(instance=instance)

    @metrics.tracker
    async def force_delete(
        self,
        instance: models.BaseSoftDeleteModelT,
    ) -> None:
        """Delete model for database."""
        await super().delete(instance=instance)
