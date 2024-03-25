import typing

import factory
import factory.fuzzy

import saritasa_sqlalchemy_tools

from . import models, repositories


class TestModelFactory(
    saritasa_sqlalchemy_tools.AsyncSQLAlchemyModelFactory[models.TestModel],
):
    """Factory to generate TestModel."""

    text = factory.Faker(
        "pystr",
        min_chars=1,
        max_chars=30,
    )
    text_enum = factory.fuzzy.FuzzyChoice(
        models.TestModel.TextEnum,
    )
    number = factory.Faker("pyint")
    small_number = factory.Faker("pyint")
    decimal_number = factory.Faker(
        "pydecimal",
        positive=True,
        left_digits=5,
        right_digits=0,
    )
    boolean = factory.Faker("pybool")
    text_list = factory.List(
        [
            factory.Faker(
                "pystr",
                min_chars=1,
                max_chars=30,
            )
            for _ in range(3)
        ],
    )
    date_time = factory.Faker("date_time")
    date = factory.Faker("date_between")
    timedelta = factory.Faker("time_delta")
    json_field = factory.Faker("pydict", allowed_types=[str, int, float])

    class Meta:
        model = models.TestModel
        repository = repositories.TestModelRepository
        sub_factories: typing.ClassVar = {
            "related_model": "tests.factories.RelatedModelFactory",
            "related_models": ("tests.factories.RelatedModelFactory", 5),
        }


class SoftDeleteTestModelFactory(
    saritasa_sqlalchemy_tools.AsyncSQLAlchemyModelFactory[
        models.SoftDeleteTestModel
    ],
):
    """Factory to generate SoftDeleteTestModel."""

    text = factory.Faker(
        "pystr",
        min_chars=200,
        max_chars=250,
    )
    text_enum = factory.fuzzy.FuzzyChoice(
        models.TestModel.TextEnum,
    )
    number = factory.Faker("pyint")
    small_number = factory.Faker("pyint")
    decimal_number = factory.Faker(
        "pydecimal",
        positive=True,
        left_digits=5,
        right_digits=0,
    )
    boolean = factory.Faker("pybool")
    text_list = factory.List(
        [
            factory.Faker(
                "pystr",
                min_chars=1,
                max_chars=30,
            )
            for _ in range(3)
        ],
    )
    date_time = factory.Faker("date_time")
    date = factory.Faker("date_between")
    timedelta = factory.Faker("time_delta")
    json_field = factory.Faker("pydict", allowed_types=[str, int, float])

    class Meta:
        model = models.SoftDeleteTestModel
        repository = repositories.SoftDeleteTestModelRepository


class RelatedModelFactory(
    saritasa_sqlalchemy_tools.AsyncSQLAlchemyModelFactory[models.RelatedModel],
):
    """Factory to generate RelatedModel."""

    class Meta:
        model = models.RelatedModel
        repository = repositories.RelatedModelRepository


class M2MModelFactory(
    saritasa_sqlalchemy_tools.AsyncSQLAlchemyModelFactory[models.M2MModel],
):
    """Factory to generate M2MModel."""

    class Meta:
        model = models.M2MModel
        repository = repositories.M2MModelRepository
        sub_factories: typing.ClassVar = {
            "related_model": "tests.factories.RelatedModelFactory",
            "test_model": "tests.factories.TestModelFactory",
        }
