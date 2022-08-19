# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2022 Jacob Lifshay

import unittest
from nmigen.hdl.ast import (AnySeq, Assert, Signal, Value, Array, Value)
from nmigen.hdl.dsl import Module
from nmigen.sim import Delay, Tick
from nmutil.formaltest import FHDLTestCase
from nmutil.plru2 import PLRU  # , PLRUs
from nmutil.sim_util import write_il, do_sim
from nmutil.plain_data import plain_data


@plain_data()
class PrettyPrintState:
    __slots__ = "indent", "file", "at_line_start"

    def __init__(self, indent=0, file=None, at_line_start=True):
        self.indent = indent
        self.file = file
        self.at_line_start = at_line_start

    def write(self, text):
        # type: (str) -> None
        for ch in text:
            if ch == "\n":
                self.at_line_start = True
            elif self.at_line_start:
                self.at_line_start = False
                print("    " * self.indent, file=self.file, end='')
            print(ch, file=self.file, end='')


@plain_data()
class PLRUNode:
    __slots__ = "id", "state", "left_child", "right_child"

    def __init__(self, id, left_child=None, right_child=None):
        # type: (int, PLRUNode | None, PLRUNode | None) -> None
        self.id = id
        self.state = Signal(name=f"state_{id}")
        self.left_child = left_child
        self.right_child = right_child

    @property
    def depth(self):
        depth = 0
        if self.left_child is not None:
            depth = max(depth, 1 + self.left_child.depth)
        if self.right_child is not None:
            depth = max(depth, 1 + self.right_child.depth)
        return depth

    def __pretty_print(self, state):
        # type: (PrettyPrintState) -> None
        state.write("PLRUNode(")
        state.indent += 1
        state.write(f"id={self.id!r},\n")
        state.write(f"state={self.state!r},\n")
        state.write("left_child=")
        if self.left_child is None:
            state.write("None")
        else:
            self.left_child.__pretty_print(state)
        state.write(",\nright_child=")
        if self.right_child is None:
            state.write("None")
        else:
            self.right_child.__pretty_print(state)
        state.indent -= 1
        state.write("\n)")

    def pretty_print(self, file=None):
        self.__pretty_print(PrettyPrintState(file=file))
        print(file=file)

    def set_states_from_index(self, m, index, ids):
        # type: (Module, Value, list[Signal]) -> None
        m.d.sync += self.state.eq(~index[-1])
        m.d.comb += ids[0].eq(self.id)
        with m.If(index[-1]):
            if self.right_child is not None:
                self.right_child.set_states_from_index(m, index[:-1], ids[1:])
        with m.Else():
            if self.left_child is not None:
                self.left_child.set_states_from_index(m, index[:-1], ids[1:])

    def get_lru(self, m, ids):
        # type: (Module, list[Signal]) -> Signal
        retval = Signal(1 + self.depth, name=f"lru_{self.id}", reset=0)
        m.d.comb += retval[-1].eq(self.state)
        m.d.comb += ids[0].eq(self.id)
        with m.If(self.state):
            if self.right_child is not None:
                right_lru = self.right_child.get_lru(m, ids[1:])
                m.d.comb += retval[:-1].eq(right_lru)
        with m.Else():
            if self.left_child is not None:
                left_lru = self.left_child.get_lru(m, ids[1:])
                m.d.comb += retval[:-1].eq(left_lru)
        return retval


class TestPLRU(FHDLTestCase):
    def tst(self, log2_num_ways, test_seq=None):
        # type: (int, list[int | None] | None) -> None

        @plain_data()
        class MyAssert:
            __slots__ = "test", "en"

            def __init__(self, test, en):
                # type: (Value, Signal) -> None
                self.test = test
                self.en = en

        asserts = []  # type: list[MyAssert]

        def assert_(test):
            if test_seq is None:
                return [Assert(test, src_loc_at=1)]
            assert_en = Signal(name="assert_en", src_loc_at=1, reset=False)
            asserts.append(MyAssert(test=test, en=assert_en))
            return [assert_en.eq(True)]

        dut = PLRU(log2_num_ways, debug=True)  # check debug works
        write_il(self, dut, ports=dut.ports())
        # debug clutters up vcd, so disable it for formal proofs
        dut = PLRU(log2_num_ways, debug=test_seq is not None)
        num_ways = 1 << log2_num_ways
        self.assertEqual(dut.log2_num_ways, log2_num_ways)
        self.assertEqual(dut.num_ways, num_ways)
        self.assertIsInstance(dut.acc_i, Signal)
        self.assertIsInstance(dut.acc_en_i, Signal)
        self.assertIsInstance(dut.lru_o, Signal)
        self.assertEqual(len(dut.acc_i), log2_num_ways)
        self.assertEqual(len(dut.acc_en_i), 1)
        self.assertEqual(len(dut.lru_o), log2_num_ways)
        write_il(self, dut, ports=dut.ports())
        m = Module()
        nodes = [PLRUNode(i) for i in range(num_ways - 1)]
        self.assertIsInstance(dut._tree, Array)
        self.assertEqual(len(dut._tree), len(nodes))
        for i in range(len(nodes)):
            if i != 0:
                parent = (i + 1) // 2 - 1
                if i % 2:
                    nodes[parent].left_child = nodes[i]
                else:
                    nodes[parent].right_child = nodes[i]
            self.assertIsInstance(dut._tree[i], Signal)
            self.assertEqual(len(dut._tree[i]), 1)
            m.d.comb += assert_(nodes[i].state == dut._tree[i])

        if test_seq is None:
            m.d.comb += [
                dut.acc_i.eq(AnySeq(log2_num_ways)),
                dut.acc_en_i.eq(AnySeq(1)),
            ]

        l2nwr = range(log2_num_ways)
        upd_ids = [Signal(log2_num_ways, name=f"upd_id_{i}") for i in l2nwr]
        with m.If(dut.acc_en_i):
            nodes[0].set_states_from_index(m, dut.acc_i, upd_ids)

            self.assertEqual(len(dut._upd_lru_nodes), len(upd_ids))
            for l, r in zip(dut._upd_lru_nodes, upd_ids):
                m.d.comb += assert_(l == r)

        get_ids = [Signal(log2_num_ways, name=f"get_id_{i}") for i in l2nwr]
        lru = Signal(log2_num_ways)
        m.d.comb += lru.eq(nodes[0].get_lru(m, get_ids))
        m.d.comb += assert_(dut.lru_o == lru)
        self.assertEqual(len(dut._get_lru_nodes), len(get_ids))
        for l, r in zip(dut._get_lru_nodes, get_ids):
            m.d.comb += assert_(l == r)

        nodes[0].pretty_print()

        m.submodules.dut = dut
        if test_seq is None:
            self.assertFormal(m, mode="prove", depth=2)
        else:
            traces = [dut.acc_i, dut.acc_en_i, *dut._tree]
            for node in nodes:
                traces.append(node.state)
            traces += [
                dut.lru_o, lru, *dut._get_lru_nodes, *get_ids,
                *dut._upd_lru_nodes, *upd_ids,
            ]

            def subtest(acc_i, acc_en_i):
                yield dut.acc_i.eq(acc_i)
                yield dut.acc_en_i.eq(acc_en_i)
                yield Tick()
                yield Delay(0.7e-6)
                for a in asserts:
                    if (yield a.en):
                        with self.subTest(
                                assert_loc=':'.join(map(str, a.en.src_loc))):
                            self.assertTrue((yield a.test))

            def process():
                for test_item in test_seq:
                    if test_item is None:
                        with self.subTest(test_item="None"):
                            yield from subtest(acc_i=0, acc_en_i=0)
                    else:
                        with self.subTest(test_item=hex(test_item)):
                            yield from subtest(acc_i=test_item, acc_en_i=1)

            with do_sim(self, m, traces) as sim:
                sim.add_clock(1e-6)
                sim.add_process(process)
                sim.run()

    def test_bits_1(self):
        self.tst(1)

    def test_bits_2(self):
        self.tst(2)

    def test_bits_3(self):
        self.tst(3)

    def test_bits_4(self):
        self.tst(4)

    def test_bits_5(self):
        self.tst(5)

    def test_bits_6(self):
        self.tst(6)

    def test_bits_3_sim(self):
        self.tst(3, [
            0x0, 0x1, 0x2, 0x3, 0x4, 0x5, 0x6, 0x7,
            None,
            0x0, 0x4, 0x2, 0x6, 0x1, 0x5, 0x3, 0x7,
            None,
        ])


if __name__ == "__main__":
    unittest.main()
