# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2022 Jacob Lifshay

import unittest
from nmigen.hdl.ast import AnyConst, Assert, Signal, Assume
from nmigen.hdl.dsl import Module
from nmutil.formaltest import FHDLTestCase
from nmutil.byterev import byte_reverse
from nmutil.grev import grev


VALID_BYTE_REVERSE_LENGTHS = tuple(1 << i for i in range(4))
LOG2_BYTE_SIZE = 3


class TestByteReverse(FHDLTestCase):
    def tst(self, log2_width, rev_length=None):
        assert isinstance(log2_width, int) and log2_width >= LOG2_BYTE_SIZE
        assert rev_length is None or rev_length in VALID_BYTE_REVERSE_LENGTHS
        m = Module()
        width = 1 << log2_width
        inp = Signal(width)
        m.d.comb += inp.eq(AnyConst(width))
        length_sig = Signal(range(max(VALID_BYTE_REVERSE_LENGTHS) + 1))
        m.d.comb += length_sig.eq(AnyConst(length_sig.shape()))

        if rev_length is None:
            rev_length = length_sig
        else:
            m.d.comb += Assume(length_sig == rev_length)

        with m.Switch(length_sig):
            for l in VALID_BYTE_REVERSE_LENGTHS:
                with m.Case(l):
                    m.d.comb += Assume(width >= l << LOG2_BYTE_SIZE)
            with m.Default():
                m.d.comb += Assume(False)

        out = byte_reverse(m, name="out", data=inp, length=rev_length)

        expected = Signal(width)
        for log2_chunk_size in range(LOG2_BYTE_SIZE, log2_width + 1):
            chunk_size = 1 << log2_chunk_size
            chunk_byte_size = chunk_size >> LOG2_BYTE_SIZE
            chunk_sizes = chunk_size - 8
            with m.If(rev_length == chunk_byte_size):
                m.d.comb += expected.eq(grev(inp, chunk_sizes, log2_width)
                                        & ((1 << chunk_size) - 1))

        m.d.comb += Assert(expected == out)

        self.assertFormal(m)

    def test_8_len_1(self):
        self.tst(log2_width=3, rev_length=1)

    def test_8(self):
        self.tst(log2_width=3)

    def test_16_len_1(self):
        self.tst(log2_width=4, rev_length=1)

    def test_16_len_2(self):
        self.tst(log2_width=4, rev_length=2)

    def test_16(self):
        self.tst(log2_width=4)

    def test_32_len_1(self):
        self.tst(log2_width=5, rev_length=1)

    def test_32_len_2(self):
        self.tst(log2_width=5, rev_length=2)

    def test_32_len_4(self):
        self.tst(log2_width=5, rev_length=4)

    def test_32(self):
        self.tst(log2_width=5)

    def test_64_len_1(self):
        self.tst(log2_width=6, rev_length=1)

    def test_64_len_2(self):
        self.tst(log2_width=6, rev_length=2)

    def test_64_len_4(self):
        self.tst(log2_width=6, rev_length=4)

    def test_64_len_8(self):
        self.tst(log2_width=6, rev_length=8)

    def test_64(self):
        self.tst(log2_width=6)

    def test_128_len_1(self):
        self.tst(log2_width=7, rev_length=1)

    def test_128_len_2(self):
        self.tst(log2_width=7, rev_length=2)

    def test_128_len_4(self):
        self.tst(log2_width=7, rev_length=4)

    def test_128_len_8(self):
        self.tst(log2_width=7, rev_length=8)

    def test_128(self):
        self.tst(log2_width=7)


if __name__ == "__main__":
    unittest.main()
