# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2021 Jacob Lifshay

# Funded by NLnet Assure Programme 2021-02-052, https://nlnet.nl/assure part
# of Horizon 2020 EU Programme 957073.

import unittest
from nmigen.hdl.ast import AnyConst, Assert, Signal
from nmigen.hdl.dsl import Module
from nmutil.formaltest import FHDLTestCase
from nmutil.lut import BitwiseMux, BitwiseLut, TreeBitwiseLut
from nmigen.sim import Delay
from nmutil.sim_util import do_sim, hash_256


class TestBitwiseMux(FHDLTestCase):
    def test(self):
        width = 2
        dut = BitwiseMux(width)

        def case(sel, t, f, expected):
            with self.subTest(sel=bin(sel), t=bin(t), f=bin(f)):
                yield dut.sel.eq(sel)
                yield dut.t.eq(t)
                yield dut.f.eq(f)
                yield Delay(1e-6)
                output = yield dut.output
                with self.subTest(output=bin(output), expected=bin(expected)):
                    self.assertEqual(expected, output)

        def process():
            for sel in range(2 ** width):
                for t in range(2 ** width):
                    for f in range(2**width):
                        expected = 0
                        for i in range(width):
                            if sel & 2 ** i:
                                if t & 2 ** i:
                                    expected |= 2 ** i
                            elif f & 2 ** i:
                                expected |= 2 ** i
                        yield from case(sel, t, f, expected)
        with do_sim(self, dut, [dut.sel, dut.t, dut.f, dut.output]) as sim:
            sim.add_process(process)
            sim.run()

    def test_formal(self):
        width = 2
        dut = BitwiseMux(width)
        m = Module()
        m.submodules.dut = dut
        m.d.comb += dut.sel.eq(AnyConst(width))
        m.d.comb += dut.f.eq(AnyConst(width))
        m.d.comb += dut.t.eq(AnyConst(width))
        for i in range(width):
            with m.If(dut.sel[i]):
                m.d.comb += Assert(dut.t[i] == dut.output[i])
            with m.Else():
                m.d.comb += Assert(dut.f[i] == dut.output[i])
        self.assertFormal(m)


class TestBitwiseLut(FHDLTestCase):
    def tst(self, cls):
        dut = cls(3, 16)
        mask = 2 ** dut.width - 1
        lut_mask = 2 ** dut.lut.width - 1

        def case(in0, in1, in2, lut):
            expected = 0
            for i in range(dut.width):
                lut_index = 0
                if in0 & 2 ** i:
                    lut_index |= 2 ** 0
                if in1 & 2 ** i:
                    lut_index |= 2 ** 1
                if in2 & 2 ** i:
                    lut_index |= 2 ** 2
                if lut & 2 ** lut_index:
                    expected |= 2 ** i
            with self.subTest(in0=bin(in0), in1=bin(in1), in2=bin(in2),
                              lut=bin(lut)):
                yield dut.inputs[0].eq(in0)
                yield dut.inputs[1].eq(in1)
                yield dut.inputs[2].eq(in2)
                yield dut.lut.eq(lut)
                yield Delay(1e-6)
                output = yield dut.output
                with self.subTest(output=bin(output), expected=bin(expected)):
                    self.assertEqual(expected, output)

        def process():
            for shift in range(dut.lut.width):
                with self.subTest(shift=shift):
                    yield from case(in0=0xAAAA, in1=0xCCCC, in2=0xF0F0,
                                    lut=1 << shift)
            for case_index in range(100):
                with self.subTest(case_index=case_index):
                    in0 = hash_256(f"{case_index} in0") & mask
                    in1 = hash_256(f"{case_index} in1") & mask
                    in2 = hash_256(f"{case_index} in2") & mask
                    lut = hash_256(f"{case_index} lut") & lut_mask
                    yield from case(in0, in1, in2, lut)
        with do_sim(self, dut, [*dut.inputs, dut.lut, dut.output]) as sim:
            sim.add_process(process)
            sim.run()

    def tst_formal(self, cls):
        dut = cls(3, 16)
        m = Module()
        m.submodules.dut = dut
        m.d.comb += dut.inputs[0].eq(AnyConst(dut.width))
        m.d.comb += dut.inputs[1].eq(AnyConst(dut.width))
        m.d.comb += dut.inputs[2].eq(AnyConst(dut.width))
        m.d.comb += dut.lut.eq(AnyConst(dut.lut.width))
        for i in range(dut.width):
            lut_index = Signal(dut.input_count, name=f"lut_index_{i}")
            for j in range(dut.input_count):
                m.d.comb += lut_index[j].eq(dut.inputs[j][i])
            for j in range(dut.lut.width):
                with m.If(lut_index == j):
                    m.d.comb += Assert(dut.lut[j] == dut.output[i])
        self.assertFormal(m)

    def test(self):
        self.tst(BitwiseLut)

    def test_tree(self):
        self.tst(TreeBitwiseLut)

    def test_formal(self):
        self.tst_formal(BitwiseLut)

    def test_tree_formal(self):
        self.tst_formal(TreeBitwiseLut)


if __name__ == "__main__":
    unittest.main()
