# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2021 Jacob Lifshay

# Funded by NLnet Assure Programme 2021-02-052, https://nlnet.nl/assure part
# of Horizon 2020 EU Programme 957073.

import weakref
from pathlib import Path


class RunCounter:
    def __init__(self):
        self.__run_counts = {}
        """dict mapping self.next() keys to the next int value returned by
        self.next()"""

    def next(self, k):
        """get a incrementing run counter for a `str` key `k`. returns an `int`."""
        retval = self.__run_counts.get(k, 0)
        self.__run_counts[k] = retval + 1
        return retval

    __RUN_COUNTERS = {}
    """dict mapping object ids (int) to a tuple of a weakref.ref to that
    object, and the corresponding RunCounter"""

    @staticmethod
    def get(obj):
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


def get_test_path(test_case, base_path):
    """get the `Path` for a particular unittest.TestCase instance
    (`test_case`). base_path is either a str or a path-like."""
    count = RunCounter.get(test_case).next(test_case.id())
    return Path(base_path) / test_case.id() / str(count)
