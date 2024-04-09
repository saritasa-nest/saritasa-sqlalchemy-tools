import datetime
import typing

import pydantic
import sqlalchemy.dialects.postgresql

PostgresRangeTypeT = typing.TypeVar("PostgresRangeTypeT", bound=typing.Any)


class PostgresRange(pydantic.BaseModel, typing.Generic[PostgresRangeTypeT]):
    """Representation of sqlalchemy.dialects.postgresql.Range."""

    model_config = pydantic.ConfigDict(from_attributes=True)

    lower: PostgresRangeTypeT | None
    upper: PostgresRangeTypeT | None
    bounds: sqlalchemy.dialects.postgresql.ranges._BoundsType = "[]"

    def to_db(
        self,
    ) -> sqlalchemy.dialects.postgresql.Range[PostgresRangeTypeT]:
        """Convert to postgres range."""
        return sqlalchemy.dialects.postgresql.Range(
            lower=self.lower,
            upper=self.upper,
            bounds=self.bounds,
        )

    def model_post_init(self, __context: dict[str, typing.Any]) -> None:
        """Adjust limit depending on bounds.

        Postgres always keeps and returns ranges in `[)` no matter how you
        save it. Thats why we need to correct it for frontend.

        """
        match self.bounds:
            case "[]":
                return  # pragma: no cover
            case "(]":
                if self.lower:  # pragma: no cover
                    self.lower = self.lower + datetime.timedelta(days=1)
            case "[)":
                if self.upper:
                    self.upper = self.upper - datetime.timedelta(days=1)
            case "()":  # pragma: no cover
                if self.lower:  # pragma: no cover
                    self.lower = self.lower + datetime.timedelta(days=1)
                if self.upper:  # pragma: no cover
                    self.upper = self.upper - datetime.timedelta(days=1)
        self.bounds = "[]"
