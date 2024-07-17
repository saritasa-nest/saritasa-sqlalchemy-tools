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
    typing.Generic[
        models.BaseModelT,
        repositories.BaseRepositoryT,
    ],
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
        repository_class: type[repositories.BaseRepositoryT] | None = getattr(
            cls._meta,
            "repository",
            None,
        )
        if not repository_class:
            raise ValueError("Repository class is not set in Meta class")
        repository = repository_class(db_session=session)

        pk_attr: str = instance.pk_field
        await repository.save(instance=instance)
        instance_from_db = await repository.fetch_first(
            **{
                pk_attr: getattr(instance, pk_attr),
            },
        )
        if not instance_from_db:
            raise ValueError(  # pragma: no cover
                "Created instance wasn't found in database",
            )
        return await cls.post_save(
            repository=repository,
            instance=instance_from_db,
            session=session,
        )

    @classmethod
    async def create_batch_async(
        cls,
        session: session.Session,
        size: int,
        **kwargs,
    ) -> list[models.BaseModelT]:
        """Create several instances."""
        return [
            await cls.create_async(
                session=session,
                **kwargs,
            )
            for _ in range(size)
        ]

    @classmethod
    async def _async_run_sub_factories(
        cls,
        session: session.Session,
        passed_fields: collections.abc.Sequence[str],
    ) -> dict[str, models.BaseModel | list[models.BaseModel]]:
        """Generate objects from sub factories."""
        sub_factories_map: dict[str, str | tuple[str, int]] = getattr(
            cls._meta,
            "sub_factories",
            {},
        )
        generated_instances: dict[
            str,
            models.BaseModel | list[models.BaseModel],
        ] = {}
        for field, sub_factory_path in sub_factories_map.items():
            if field in passed_fields or f"{field}_id" in passed_fields:
                continue
            if isinstance(sub_factory_path, str):
                *factory_module, sub_factory_name = sub_factory_path.split(".")
                sub_factory = getattr(
                    importlib.import_module(".".join(factory_module)),
                    sub_factory_name,
                )
                generated_instances[field] = await sub_factory.create_async(
                    session=session,
                )
            else:
                sub_factory_path, size = sub_factory_path
                *factory_module, sub_factory_name = sub_factory_path.split(".")
                sub_factory = getattr(
                    importlib.import_module(".".join(factory_module)),
                    sub_factory_name,
                )
                generated_instances[
                    field
                ] = await sub_factory.create_batch_async(
                    session=session,
                    size=size,
                )
        return generated_instances

    @classmethod
    async def post_save(
        cls,
        repository: repositories.BaseRepositoryT,
        instance: models.BaseModelT,
        session: session.Session,
    ) -> models.BaseModelT:
        """Preform actions after instance was generated."""
        return instance
