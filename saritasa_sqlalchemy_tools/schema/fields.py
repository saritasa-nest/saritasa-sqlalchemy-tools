import datetime
import enum
import typing

import pydantic
import sqlalchemy.dialects.postgresql

from . import enums

PostgresRangeTypeT = typing.TypeVar("PostgresRangeTypeT", bound=typing.Any)


class PostgresRangeBound(
    enums.OpenAPIDocsEnumMixin,
    enum.StrEnum,
):
    """Describe bounds for PostgresRange."""

    include_include = "[]"
    exclude_exclude = "()"
    include_exclude = "[)"
    exclude_include = "(]"


class PostgresRange(pydantic.BaseModel, typing.Generic[PostgresRangeTypeT]):
    """Representation of sqlalchemy.dialects.postgresql.Range."""

    model_config = pydantic.ConfigDict(from_attributes=True)

    lower: PostgresRangeTypeT | None
    upper: PostgresRangeTypeT | None
    bounds: PostgresRangeBound = PostgresRangeBound.include_include

    def to_db(
        self,
    ) -> sqlalchemy.dialects.postgresql.Range[PostgresRangeTypeT]:
        """Convert to postgres range."""
        return sqlalchemy.dialects.postgresql.Range(
            lower=self.lower,
            upper=self.upper,
            bounds=self.bounds.value,
        )

    @pydantic.model_validator(mode="after")
    def validate_bounds(self) -> typing.Self:
        """Validate range bounds."""
        if self.lower is None or self.upper is None:
            return self
        if self.lower > self.upper:
            raise ValueError("Lower must be equal or less than upper limit")
        return self


class PostgresDateRange(PostgresRange[datetime.date]):
    """Date range for postgres."""

    def model_post_init(self, __context: dict[str, typing.Any]) -> None:
        """Adjust limit depending on bounds.

        Postgres always keeps and returns ranges in `[)` no matter how you
        save it. Thats why we need to correct it for frontend.

        """
        match self.bounds:
            case PostgresRangeBound.include_include:
                return  # pragma: no cover
            case PostgresRangeBound.exclude_include:
                if self.lower:  # pragma: no cover
                    self.lower = self.lower + datetime.timedelta(days=1)
            case PostgresRangeBound.include_exclude:
                if self.upper:
                    self.upper = self.upper - datetime.timedelta(days=1)
            case PostgresRangeBound.exclude_exclude:  # pragma: no cover
                if self.lower:  # pragma: no cover
                    self.lower = self.lower + datetime.timedelta(days=1)
                if self.upper:  # pragma: no cover
                    self.upper = self.upper - datetime.timedelta(days=1)
        self.bounds = PostgresRangeBound.include_include
