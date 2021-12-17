# SPDX-License-Identifier: LGPL-3-or-later
# XXX - this is insufficient See Notices.txt for copyright information - XXX
# XXX TODO: add individual copyright

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
    def test(self):
        log2_width = 6
        width = 2 ** log2_width
        dut = GRev(log2_width)
        self.assertEqual(width, dut.width)

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
                for i, step in enumerate(dut._steps):
                    cur_chunk_sizes = chunk_sizes & (2 ** i - 1)
                    step_expected = grev(inval, cur_chunk_sizes, log2_width)
                    step = yield step
                    with self.subTest(i=i, step=hex(step),
                                      cur_chunk_sizes=bin(cur_chunk_sizes),
                                      step_expected=hex(step_expected)):
                        self.assertEqual(step, step_expected)

        def process():
            self.assertEqual(len(dut._steps), log2_width + 1)
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

    def test_formal(self):
        log2_width = 4
        dut = GRev(log2_width)
        m = Module()
        m.submodules.dut = dut
        m.d.comb += dut.input.eq(AnyConst(2 ** log2_width))
        m.d.comb += dut.chunk_sizes.eq(AnyConst(log2_width))
        # actual formal correctness proof is inside the module itself, now
        self.assertFormal(m)


if __name__ == "__main__":
    unittest.main()
