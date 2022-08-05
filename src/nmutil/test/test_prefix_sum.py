# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2022 Jacob Lifshay programmerjake@gmail.com

# Funded by NLnet Assure Programme 2021-02-052, https://nlnet.nl/assure part
# of Horizon 2020 EU Programme 957073.

from functools import reduce
from nmutil.formaltest import FHDLTestCase
from nmutil.sim_util import write_il
from itertools import accumulate
import operator
from nmutil.prefix_sum import (Op, pop_count, prefix_sum,
                               render_prefix_sum_diagram,
                               tree_reduction, tree_reduction_ops)
import unittest
from nmigen.hdl.ast import Signal, AnyConst, Assert
from nmigen.hdl.dsl import Module


def reference_prefix_sum(items, fn):
    return list(accumulate(items, fn))


class TestPrefixSum(FHDLTestCase):
    maxDiff = None

    def test_prefix_sum_str(self):
        input_items = ("a", "b", "c", "d", "e", "f", "g", "h", "i")
        expected = reference_prefix_sum(input_items, operator.add)
        with self.subTest(expected=repr(expected)):
            non_work_efficient = prefix_sum(input_items, work_efficient=False)
            self.assertEqual(expected, non_work_efficient)
        with self.subTest(expected=repr(expected)):
            work_efficient = prefix_sum(input_items, work_efficient=True)
            self.assertEqual(expected, work_efficient)

    def test_tree_reduction_str(self):
        input_items = ("a", "b", "c", "d", "e", "f", "g", "h", "i")
        expected = reduce(operator.add, input_items)
        with self.subTest(expected=repr(expected)):
            work_efficient = tree_reduction(input_items)
            self.assertEqual(expected, work_efficient)

    def test_tree_reduction_ops_9(self):
        ops = list(tree_reduction_ops(9))
        self.assertEqual(ops, [
            Op(out=8, lhs=7, rhs=8, row=0),
            Op(out=6, lhs=5, rhs=6, row=0),
            Op(out=4, lhs=3, rhs=4, row=0),
            Op(out=2, lhs=1, rhs=2, row=0),
            Op(out=8, lhs=6, rhs=8, row=1),
            Op(out=4, lhs=2, rhs=4, row=1),
            Op(out=8, lhs=4, rhs=8, row=2),
            Op(out=8, lhs=0, rhs=8, row=3),
        ])

    def test_tree_reduction_ops_8(self):
        ops = list(tree_reduction_ops(8))
        self.assertEqual(ops, [
            Op(out=7, lhs=6, rhs=7, row=0),
            Op(out=5, lhs=4, rhs=5, row=0),
            Op(out=3, lhs=2, rhs=3, row=0),
            Op(out=1, lhs=0, rhs=1, row=0),
            Op(out=7, lhs=5, rhs=7, row=1),
            Op(out=3, lhs=1, rhs=3, row=1),
            Op(out=7, lhs=3, rhs=7, row=2),
        ])

    def tst_pop_count_int(self, width):
        assert isinstance(width, int)
        for v in range(1 << width):
            expected = f"{v:b}".count("1")
            with self.subTest(v=v, expected=expected):
                self.assertEqual(expected, pop_count(v, width=width))

    def test_pop_count_int_0(self):
        self.tst_pop_count_int(0)

    def test_pop_count_int_1(self):
        self.tst_pop_count_int(1)

    def test_pop_count_int_2(self):
        self.tst_pop_count_int(2)

    def test_pop_count_int_3(self):
        self.tst_pop_count_int(3)

    def test_pop_count_int_4(self):
        self.tst_pop_count_int(4)

    def test_pop_count_int_5(self):
        self.tst_pop_count_int(5)

    def test_pop_count_int_6(self):
        self.tst_pop_count_int(6)

    def test_pop_count_int_7(self):
        self.tst_pop_count_int(7)

    def test_pop_count_int_8(self):
        self.tst_pop_count_int(8)

    def test_pop_count_int_9(self):
        self.tst_pop_count_int(9)

    def test_pop_count_int_10(self):
        self.tst_pop_count_int(10)

    def tst_pop_count_formal(self, width):
        assert isinstance(width, int)
        m = Module()
        v = Signal(width)
        out = Signal(16)

        def process_temporary(v):
            sig = Signal.like(v)
            m.d.comb += sig.eq(v)
            return sig

        m.d.comb += out.eq(pop_count(v, process_temporary=process_temporary))
        write_il(self, m, [v, out])
        m.d.comb += v.eq(AnyConst(width))
        expected = Signal(16)
        m.d.comb += expected.eq(reduce(operator.add,
                                       (v[i] for i in range(width)),
                                       0))
        m.d.comb += Assert(out == expected)
        self.assertFormal(m)

    def test_pop_count_formal_0(self):
        self.tst_pop_count_formal(0)

    def test_pop_count_formal_1(self):
        self.tst_pop_count_formal(1)

    def test_pop_count_formal_2(self):
        self.tst_pop_count_formal(2)

    def test_pop_count_formal_3(self):
        self.tst_pop_count_formal(3)

    def test_pop_count_formal_4(self):
        self.tst_pop_count_formal(4)

    def test_pop_count_formal_5(self):
        self.tst_pop_count_formal(5)

    def test_pop_count_formal_6(self):
        self.tst_pop_count_formal(6)

    def test_pop_count_formal_7(self):
        self.tst_pop_count_formal(7)

    def test_pop_count_formal_8(self):
        self.tst_pop_count_formal(8)

    def test_pop_count_formal_9(self):
        self.tst_pop_count_formal(9)

    def test_pop_count_formal_10(self):
        self.tst_pop_count_formal(10)

    def test_render_work_efficient(self):
        text = render_prefix_sum_diagram(16, work_efficient=True, plus="@")
        expected = r"""
 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
 ●  |  ●  |  ●  |  ●  |  ●  |  ●  |  ●  |  ●  |
 |\ |  |\ |  |\ |  |\ |  |\ |  |\ |  |\ |  |\ |
 | \|  | \|  | \|  | \|  | \|  | \|  | \|  | \|
 |  @  |  @  |  @  |  @  |  @  |  @  |  @  |  @
 |  |\ |  |  |  |\ |  |  |  |\ |  |  |  |\ |  |
 |  | \|  |  |  | \|  |  |  | \|  |  |  | \|  |
 |  |  X  |  |  |  X  |  |  |  X  |  |  |  X  |
 |  |  |\ |  |  |  |\ |  |  |  |\ |  |  |  |\ |
 |  |  | \|  |  |  | \|  |  |  | \|  |  |  | \|
 |  |  |  @  |  |  |  @  |  |  |  @  |  |  |  @
 |  |  |  |\ |  |  |  |  |  |  |  |\ |  |  |  |
 |  |  |  | \|  |  |  |  |  |  |  | \|  |  |  |
 |  |  |  |  X  |  |  |  |  |  |  |  X  |  |  |
 |  |  |  |  |\ |  |  |  |  |  |  |  |\ |  |  |
 |  |  |  |  | \|  |  |  |  |  |  |  | \|  |  |
 |  |  |  |  |  X  |  |  |  |  |  |  |  X  |  |
 |  |  |  |  |  |\ |  |  |  |  |  |  |  |\ |  |
 |  |  |  |  |  | \|  |  |  |  |  |  |  | \|  |
 |  |  |  |  |  |  X  |  |  |  |  |  |  |  X  |
 |  |  |  |  |  |  |\ |  |  |  |  |  |  |  |\ |
 |  |  |  |  |  |  | \|  |  |  |  |  |  |  | \|
 |  |  |  |  |  |  |  @  |  |  |  |  |  |  |  @
 |  |  |  |  |  |  |  |\ |  |  |  |  |  |  |  |
 |  |  |  |  |  |  |  | \|  |  |  |  |  |  |  |
 |  |  |  |  |  |  |  |  X  |  |  |  |  |  |  |
 |  |  |  |  |  |  |  |  |\ |  |  |  |  |  |  |
 |  |  |  |  |  |  |  |  | \|  |  |  |  |  |  |
 |  |  |  |  |  |  |  |  |  X  |  |  |  |  |  |
 |  |  |  |  |  |  |  |  |  |\ |  |  |  |  |  |
 |  |  |  |  |  |  |  |  |  | \|  |  |  |  |  |
 |  |  |  |  |  |  |  |  |  |  X  |  |  |  |  |
 |  |  |  |  |  |  |  |  |  |  |\ |  |  |  |  |
 |  |  |  |  |  |  |  |  |  |  | \|  |  |  |  |
 |  |  |  |  |  |  |  |  |  |  |  X  |  |  |  |
 |  |  |  |  |  |  |  |  |  |  |  |\ |  |  |  |
 |  |  |  |  |  |  |  |  |  |  |  | \|  |  |  |
 |  |  |  |  |  |  |  |  |  |  |  |  X  |  |  |
 |  |  |  |  |  |  |  |  |  |  |  |  |\ |  |  |
 |  |  |  |  |  |  |  |  |  |  |  |  | \|  |  |
 |  |  |  |  |  |  |  |  |  |  |  |  |  X  |  |
 |  |  |  |  |  |  |  |  |  |  |  |  |  |\ |  |
 |  |  |  |  |  |  |  |  |  |  |  |  |  | \|  |
 |  |  |  |  |  |  |  |  |  |  |  |  |  |  X  |
 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |\ |
 |  |  |  |  |  |  |  |  |  |  |  |  |  |  | \|
 |  |  |  |  |  |  |  ●  |  |  |  |  |  |  |  @
 |  |  |  |  |  |  |  |\ |  |  |  |  |  |  |  |
 |  |  |  |  |  |  |  | \|  |  |  |  |  |  |  |
 |  |  |  |  |  |  |  |  X  |  |  |  |  |  |  |
 |  |  |  |  |  |  |  |  |\ |  |  |  |  |  |  |
 |  |  |  |  |  |  |  |  | \|  |  |  |  |  |  |
 |  |  |  |  |  |  |  |  |  X  |  |  |  |  |  |
 |  |  |  |  |  |  |  |  |  |\ |  |  |  |  |  |
 |  |  |  |  |  |  |  |  |  | \|  |  |  |  |  |
 |  |  |  |  |  |  |  |  |  |  X  |  |  |  |  |
 |  |  |  |  |  |  |  |  |  |  |\ |  |  |  |  |
 |  |  |  |  |  |  |  |  |  |  | \|  |  |  |  |
 |  |  |  ●  |  |  |  ●  |  |  |  @  |  |  |  |
 |  |  |  |\ |  |  |  |\ |  |  |  |\ |  |  |  |
 |  |  |  | \|  |  |  | \|  |  |  | \|  |  |  |
 |  |  |  |  X  |  |  |  X  |  |  |  X  |  |  |
 |  |  |  |  |\ |  |  |  |\ |  |  |  |\ |  |  |
 |  |  |  |  | \|  |  |  | \|  |  |  | \|  |  |
 |  ●  |  ●  |  @  |  ●  |  @  |  ●  |  @  |  |
 |  |\ |  |\ |  |\ |  |\ |  |\ |  |\ |  |\ |  |
 |  | \|  | \|  | \|  | \|  | \|  | \|  | \|  |
 |  |  @  |  @  |  @  |  @  |  @  |  @  |  @  |
 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
"""
        expected = expected[1:-1]  # trim newline at start and end
        if text != expected:
            print("text:")
            print(text)
            print()
        self.assertEqual(expected, text)

    def test_render_not_work_efficient(self):
        text = render_prefix_sum_diagram(16, work_efficient=False, plus="@")
        expected = r"""
 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
 ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  ●  |
 |\ |\ |\ |\ |\ |\ |\ |\ |\ |\ |\ |\ |\ |\ |\ |
 | \| \| \| \| \| \| \| \| \| \| \| \| \| \| \|
 ●  @  @  @  @  @  @  @  @  @  @  @  @  @  @  @
 |\ |\ |\ |\ |\ |\ |\ |\ |\ |\ |\ |\ |\ |\ |  |
 | \| \| \| \| \| \| \| \| \| \| \| \| \| \|  |
 |  X  X  X  X  X  X  X  X  X  X  X  X  X  X  |
 |  |\ |\ |\ |\ |\ |\ |\ |\ |\ |\ |\ |\ |\ |\ |
 |  | \| \| \| \| \| \| \| \| \| \| \| \| \| \|
 ●  ●  @  @  @  @  @  @  @  @  @  @  @  @  @  @
 |\ |\ |\ |\ |\ |\ |\ |\ |\ |\ |\ |\ |  |  |  |
 | \| \| \| \| \| \| \| \| \| \| \| \|  |  |  |
 |  X  X  X  X  X  X  X  X  X  X  X  X  |  |  |
 |  |\ |\ |\ |\ |\ |\ |\ |\ |\ |\ |\ |\ |  |  |
 |  | \| \| \| \| \| \| \| \| \| \| \| \|  |  |
 |  |  X  X  X  X  X  X  X  X  X  X  X  X  |  |
 |  |  |\ |\ |\ |\ |\ |\ |\ |\ |\ |\ |\ |\ |  |
 |  |  | \| \| \| \| \| \| \| \| \| \| \| \|  |
 |  |  |  X  X  X  X  X  X  X  X  X  X  X  X  |
 |  |  |  |\ |\ |\ |\ |\ |\ |\ |\ |\ |\ |\ |\ |
 |  |  |  | \| \| \| \| \| \| \| \| \| \| \| \|
 ●  ●  ●  ●  @  @  @  @  @  @  @  @  @  @  @  @
 |\ |\ |\ |\ |\ |\ |\ |\ |  |  |  |  |  |  |  |
 | \| \| \| \| \| \| \| \|  |  |  |  |  |  |  |
 |  X  X  X  X  X  X  X  X  |  |  |  |  |  |  |
 |  |\ |\ |\ |\ |\ |\ |\ |\ |  |  |  |  |  |  |
 |  | \| \| \| \| \| \| \| \|  |  |  |  |  |  |
 |  |  X  X  X  X  X  X  X  X  |  |  |  |  |  |
 |  |  |\ |\ |\ |\ |\ |\ |\ |\ |  |  |  |  |  |
 |  |  | \| \| \| \| \| \| \| \|  |  |  |  |  |
 |  |  |  X  X  X  X  X  X  X  X  |  |  |  |  |
 |  |  |  |\ |\ |\ |\ |\ |\ |\ |\ |  |  |  |  |
 |  |  |  | \| \| \| \| \| \| \| \|  |  |  |  |
 |  |  |  |  X  X  X  X  X  X  X  X  |  |  |  |
 |  |  |  |  |\ |\ |\ |\ |\ |\ |\ |\ |  |  |  |
 |  |  |  |  | \| \| \| \| \| \| \| \|  |  |  |
 |  |  |  |  |  X  X  X  X  X  X  X  X  |  |  |
 |  |  |  |  |  |\ |\ |\ |\ |\ |\ |\ |\ |  |  |
 |  |  |  |  |  | \| \| \| \| \| \| \| \|  |  |
 |  |  |  |  |  |  X  X  X  X  X  X  X  X  |  |
 |  |  |  |  |  |  |\ |\ |\ |\ |\ |\ |\ |\ |  |
 |  |  |  |  |  |  | \| \| \| \| \| \| \| \|  |
 |  |  |  |  |  |  |  X  X  X  X  X  X  X  X  |
 |  |  |  |  |  |  |  |\ |\ |\ |\ |\ |\ |\ |\ |
 |  |  |  |  |  |  |  | \| \| \| \| \| \| \| \|
 |  |  |  |  |  |  |  |  @  @  @  @  @  @  @  @
 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
"""
        expected = expected[1:-1]  # trim newline at start and end
        if text != expected:
            print("text:")
            print(text)
            print()
        self.assertEqual(expected, text)

    # TODO: add more tests


if __name__ == "__main__":
    unittest.main()
