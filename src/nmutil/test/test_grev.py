# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2021 Jacob Lifshay

# Funded by NLnet Assure Programme 2021-02-052, https://nlnet.nl/assure part
# of Horizon 2020 EU Programme 957073.

import unittest
from nmigen.hdl.ast import AnyConst, Assert
from nmigen.hdl.dsl import Module
from nmutil.formaltest import FHDLTestCase
from nmutil.grev import GRev, grev
from nmigen.sim import Delay
from nmutil.sim_util import do_sim, hash_256


class TestGrev(FHDLTestCase):
    def tst(self, msb_first, log2_width=6):
        width = 2 ** log2_width
        dut = GRev(log2_width, msb_first)
        self.assertEqual(width, dut.width)
        self.assertEqual(len(dut._intermediates), log2_width + 1)

        def case(inval, chunk_sizes):
            expected = grev(inval, chunk_sizes, log2_width)
            with self.subTest(inval=hex(inval), chunk_sizes=bin(chunk_sizes),
                              expected=hex(expected)):
                yield dut.input.eq(inval)
                yield dut.chunk_sizes.eq(chunk_sizes)
                yield Delay(1e-6)
                output = yield dut.output
                with self.subTest(output=hex(output)):
                    self.assertEqual(expected, output)
                for sig, expected in dut._sigs_and_expected(inval,
                                                            chunk_sizes):
                    value = yield sig
                    with self.subTest(sig=sig.name, value=hex(value),
                                      expected=hex(expected)):
                        self.assertEqual(value, expected)

        def process():
            for count in range(width + 1):
                inval = (1 << count) - 1
                for chunk_sizes in range(2 ** log2_width):
                    yield from case(inval, chunk_sizes)
            for i in range(100):
                inval = hash_256(f"grev input {i}")
                inval &= 2 ** width - 1
                chunk_sizes = hash_256(f"grev 2 {i}")
                chunk_sizes &= 2 ** log2_width - 1
                yield from case(inval, chunk_sizes)
        with do_sim(self, dut, [dut.input, dut.chunk_sizes,
                                dut.output]) as sim:
            sim.add_process(process)
            sim.run()

    def test(self):
        self.tst(msb_first=False)

    def test_msb_first(self):
        self.tst(msb_first=True)

    def test_small(self):
        self.tst(msb_first=False, log2_width=3)

    def test_small_msb_first(self):
        self.tst(msb_first=True, log2_width=3)

    def tst_formal(self, msb_first):
        log2_width = 4
        dut = GRev(log2_width, msb_first)
        m = Module()
        m.submodules.dut = dut
        m.d.comb += dut.input.eq(AnyConst(2 ** log2_width))
        m.d.comb += dut.chunk_sizes.eq(AnyConst(log2_width))
        # actual formal correctness proof is inside the module itself, now
        self.assertFormal(m)

    def test_formal(self):
        self.tst_formal(msb_first=False)

    def test_formal_msb_first(self):
        self.tst_formal(msb_first=True)


if __name__ == "__main__":
    unittest.main()
