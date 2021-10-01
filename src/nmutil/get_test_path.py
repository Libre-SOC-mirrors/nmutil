# SPDX-License-Identifier: LGPL-3-or-later
# See Notices.txt for copyright information

from os import PathLike
from typing import Dict, Tuple, Union
import unittest
import weakref
from pathlib import Path


class RunCounter:
    __run_counts: Dict[str, int]

    def __init__(self) -> None:
        self.__run_counts = {}

    def next(self, k: str) -> int:
        retval = self.__run_counts.get(k, 0)
        self.__run_counts[k] = retval + 1
        return retval

    __RUN_COUNTERS: Dict[int, Tuple[weakref.ref, "RunCounter"]] = {}

    @staticmethod
    def get(obj: object) -> "RunCounter":
        k = id(obj)
        t = RunCounter.__RUN_COUNTERS
        try:
            return t[k][1]
        except KeyError:
            retval = RunCounter()

            def on_finalize(obj):
                del t[k]
            t[k] = weakref.ref(obj, on_finalize), retval
            return retval


_StrPath = Union[str, PathLike]


def get_test_path(test_case: unittest.TestCase, base_path: _StrPath) -> Path:
    count = RunCounter.get(test_case).next(test_case.id())
    return Path(base_path) / test_case.id() / str(count)
