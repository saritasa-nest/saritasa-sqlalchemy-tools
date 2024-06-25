import collections.abc
import contextlib
import functools
import importlib
import os
import typing

FP = typing.ParamSpec("FP")  # Function Parameters
RV = typing.TypeVar("RV")  # Returned Value


def tracker(
    func: collections.abc.Callable[FP, RV],
) -> collections.abc.Callable[FP, RV]:
    """Create a placeholder for performance tracker."""

    @functools.wraps(func)
    def wrapper_tracker(
        *args: FP.args,
        **kwargs: FP.kwargs,
    ) -> RV:
        return func(*args, **kwargs)

    return wrapper_tracker


with contextlib.suppress(KeyError):  # pragma: no cover
    metric_tracker_path = os.environ[
        "SARITASA_SQLALCHEMY_TOOLS_METRIC_TRACKER"
    ]
    *module, tracker_name = metric_tracker_path.split(".")
    tracker = getattr(importlib.import_module(".".join(module)), tracker_name)  # noqa: F811

__all__ = ("tracker",)
