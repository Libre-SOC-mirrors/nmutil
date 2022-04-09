# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2022 Jacob Lifshay programmerjake@gmail.com

# Funded by NLnet Assure Programme 2021-02-052, https://nlnet.nl/assure part
# of Horizon 2020 EU Programme 957073.

from nmutil.formaltest import FHDLTestCase
from itertools import accumulate
import operator
from nmutil.prefix_sum import prefix_sum
import unittest


def reference_prefix_sum(items, fn):
    return list(accumulate(items, fn))


class TestPrefixSum(FHDLTestCase):
    def test_prefix_sum_str(self):
        input_items = ("a", "b", "c", "d", "e", "f", "g", "h", "i")
        expected = reference_prefix_sum(input_items, operator.add)
        with self.subTest(expected=repr(expected)):
            non_work_efficient = prefix_sum(input_items, work_efficient=False)
            self.assertEqual(expected, non_work_efficient)
        with self.subTest(expected=repr(expected)):
            work_efficient = prefix_sum(input_items, work_efficient=True)
            self.assertEqual(expected, work_efficient)

    # TODO: add more tests


if __name__ == "__main__":
    unittest.main()
