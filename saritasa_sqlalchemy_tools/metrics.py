import collections.abc
import contextlib
import functools
import importlib
import os
import typing


def tracker(
    func: collections.abc.Callable[..., typing.Any],
) -> typing.Any:
    """Create a placeholder for performance tracker."""

    @functools.wraps(func)
    def wrapper_tracker(*args: typing.Any, **kwargs: typing.Any) -> typing.Any:
        return func(*args, **kwargs)

    return wrapper_tracker


with contextlib.suppress(KeyError):  # pragma: no cover
    metric_tracker_path = os.environ[
        "SARITASA_SQLALCHEMY_TOOLS_METRIC_TRACKER"
    ]
    *module, tracker_name = metric_tracker_path.split(".")
    tracker = getattr(importlib.import_module(".".join(module)), tracker_name)  # noqa: F811

__all__ = ("tracker",)
