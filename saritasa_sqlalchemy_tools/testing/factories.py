import collections.abc
import importlib
import typing

import factory

from .. import models, repositories, session


class AsyncSQLAlchemyOptions(factory.alchemy.SQLAlchemyOptions):
    """Meta options for AsyncSQLAlchemyModelFactory."""

    def _build_default_options(self) -> list[factory.base.OptionDefault]:
        return [
            *super()._build_default_options(),
            factory.base.OptionDefault("repository", None, inherit=True),
            factory.base.OptionDefault("sub_factories", {}, inherit=True),
        ]


class AsyncSQLAlchemyModelFactory(
    factory.alchemy.SQLAlchemyModelFactory,
    typing.Generic[models.BaseModelT],
):
    """Factory with ability to create instances asynchronously."""

    _options_class = AsyncSQLAlchemyOptions

    @classmethod
    async def create_async(
        cls,
        session: session.Session,
        **kwargs,
    ) -> models.BaseModelT:
        """Create instance in database."""
        kwargs.update(
            **await cls._async_run_sub_factories(
                session=session,
                passed_fields=list(kwargs.keys()),
            ),
        )
        instance: models.BaseModelT = cls.build(**kwargs)
        repository_class: (
            type[repositories.BaseRepository[models.BaseModelT,]] | None
        ) = getattr(
            cls._meta,
            "repository",
            None,
        )
        if not repository_class:
            raise ValueError("Repository class in not set in Meta class")
        repository = repository_class(db_session=session)

        pk_attr: str = instance.pk_field
        await repository.save(instance=instance)
        instance_from_db = (
            await repository.fetch(
                **{
                    pk_attr: getattr(instance, pk_attr),
                },
            )
        ).first()
        if not instance_from_db:
            raise ValueError("Created instance wasn't found in database")
        return instance_from_db

    @classmethod
    async def create_batch_async(
        cls,
        session: session.Session,
        size: int,
        **kwargs,
    ) -> list[models.BaseModelT]:
        """Create several instances."""
        instances: list[models.BaseModelT] = []
        for _ in range(size):
            instances.append(
                await cls.create_async(
                    session=session,
                    **kwargs,
                ),
            )
        return instances

    @classmethod
    async def _async_run_sub_factories(
        cls,
        session: session.Session,
        passed_fields: collections.abc.Sequence[str],
    ) -> dict[str, models.BaseModel]:
        """Generate objects from sub factories."""
        sub_factories_map: dict[str, str] = getattr(
            cls._meta,
            "sub_factories",
            {},
        )
        generated_instances: dict[str, models.BaseModel] = {}
        for field, sub_factory_path in sub_factories_map.items():
            if field in passed_fields or f"{field}_id" in passed_fields:
                continue
            *factory_module, sub_factory_name = sub_factory_path.split(".")
            sub_factory: typing.Self = getattr(
                importlib.import_module(".".join(factory_module)),
                sub_factory_name,
            )
            generated_instances[field] = await sub_factory.create_async(
                session=session,
            )
        return generated_instances
