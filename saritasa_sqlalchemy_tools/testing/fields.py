import datetime

import factory
import faker
import sqlalchemy.dialects.postgresql


class DateRangeFactory(factory.LazyAttribute):
    """Generate date range."""

    def __init__(
        self,
        start_date: str = "-3d",
        end_date: str = "+3d",
    ) -> None:
        self.start_date = start_date
        self.end_date = end_date
        super().__init__(
            function=self._generate_date_range,
        )

    def _generate_date_range(
        self,
        *args,  # noqa: ANN002
        **kwargs,
    ) -> sqlalchemy.dialects.postgresql.Range[datetime.date]:
        """Generate range."""
        fake = faker.Faker()
        lower = fake.date_between(
            start_date=self.start_date,
            end_date=self.end_date,
        )
        upper = fake.date_between(
            start_date=lower,
            end_date=self.end_date,
        )
        # Need to make sure that the dates are not the same
        if upper == lower:
            upper += datetime.timedelta(days=1)

        return sqlalchemy.dialects.postgresql.Range(
            lower=lower,
            upper=upper,
            bounds="[)",
        )
