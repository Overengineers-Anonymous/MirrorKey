import functools
from typing import Any, Callable
import pytest
import inspect


class Param:
    def __init__(self, data: Any, test_id: str):
        self.data = data
        self.test_id = test_id


def parametrise(data: list[Param]):
    if not data:
        raise Exception("Param Data is empty")

    def decorator(func: Callable):
        @functools.wraps(func)
        def inner(*args, **kwargs):
            return func(*args, **kwargs)

        args = inspect.getfullargspec(func)[0]

        args_name = ",".join(args)
        param_data = [datum.data if len(args) != 1 else datum.data[0] for datum in data]
        ids = [datum.test_id for datum in data]

        length = len(data[0].data)
        if len(args) != 1:
            for length_data in [*param_data, args]:
                if len(length_data) != length:
                    raise Exception("Param Data length mismatch")
        return pytest.mark.parametrize(args_name, param_data, ids=ids)(inner)

    return decorator
