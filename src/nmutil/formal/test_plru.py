# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2022 Jacob Lifshay

import unittest
from nmigen.hdl.ast import (AnySeq, Assert, Signal, Assume, Const,
                            unsigned, AnyConst, Value)
from nmigen.hdl.dsl import Module
from nmutil.formaltest import FHDLTestCase
from nmutil.plru import PLRU, PLRUs
from nmutil.sim_util import write_il
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
    __slots__ = "state", "left_child", "right_child"

    def __init__(self, state, left_child=None, right_child=None):
        # type: (Signal, PLRUNode | None, PLRUNode | None) -> None
        self.state = state
        self.left_child = left_child
        self.right_child = right_child

    def __pretty_print(self, state):
        # type: (PrettyPrintState) -> None
        state.write("PLRUNode(")
        state.indent += 1
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

    def set_states_from_index(self, m, index):
        # type: (Module, Value) -> None
        m.d.sync += self.state.eq(index[-1])
        with m.If(index[-1]):
            if self.left_child is not None:
                self.left_child.set_states_from_index(m, index[:-1])
        with m.Else():
            if self.right_child is not None:
                self.right_child.set_states_from_index(m, index[:-1])


class TestPLRU(FHDLTestCase):
    @unittest.skip("not finished yet")
    def tst(self, BITS):
        # type: (int) -> None

        # FIXME: figure out what BITS is supposed to mean -- I would have
        # expected it to be the number of cache ways, or the number of state
        # bits in PLRU, but it's neither of those, making me think whoever
        # converted the code botched their math.
        #
        # Until that's figured out, this test is broken.

        dut = PLRU(BITS)
        write_il(self, dut, ports=dut.ports())
        m = Module()
        nodes = [PLRUNode(Signal(name=f"state_{i}")) for i in range(dut.TLBSZ)]
        self.assertEqual(len(dut._plru_tree), len(nodes))
        for i in range(1, dut.TLBSZ):
            parent = (i + 1) // 2 - 1
            if i % 2:
                nodes[parent].left_child = nodes[i]
            else:
                nodes[parent].right_child = nodes[i]
            m.d.comb += Assert(nodes[i].state == dut._plru_tree[i])

        in_index = Signal(range(BITS))

        m.d.comb += [
            in_index.eq(AnySeq(range(BITS))),
            Assume(in_index < BITS),
            dut.acc_i.eq(1 << in_index),
            dut.acc_en.eq(AnySeq(1)),
        ]

        with m.If(dut.acc_en):
            nodes[0].set_states_from_index(m, in_index)

        nodes[0].pretty_print()

        m.submodules.dut = dut
        self.assertFormal(m, mode="prove")

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

    def test_bits_7(self):
        self.tst(7)

    def test_bits_8(self):
        self.tst(8)

    def test_bits_9(self):
        self.tst(9)

    def test_bits_10(self):
        self.tst(10)

    def test_bits_11(self):
        self.tst(11)

    def test_bits_12(self):
        self.tst(12)

    def test_bits_13(self):
        self.tst(13)

    def test_bits_14(self):
        self.tst(14)

    def test_bits_15(self):
        self.tst(15)

    def test_bits_16(self):
        self.tst(16)


if __name__ == "__main__":
    unittest.main()
