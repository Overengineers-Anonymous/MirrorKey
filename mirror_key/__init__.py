import functools
from typing import Any, Callable
import pytest
import inspect

class Param:
    def __init__(self, data: Any, test_id: str):
        self.data = data
        self.test_id = test_id

def parametrize(data: list[Param]):
    if not data:
        raise Exception("Param Data is empty")

    @functools.wraps
    def inner(func: Callable):
        args = inspect.getfullargspec(func)[0]

        args_name = ",".join(args)
        param_data = [datum.data for datum in data]
        ids = [datum.test_id for datum in data]

        length = len(data[0].data)
        for length_data in [*param_data, args]:
            if len(length_data) != length:
                raise Exception("Param Data length mismatch")

        return pytest.mark.parametrize(args_name, param_data, ids=ids)(func)
    return inner
