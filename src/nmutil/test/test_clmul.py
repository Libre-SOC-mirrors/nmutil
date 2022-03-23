# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2021 Jacob Lifshay

# Funded by NLnet Assure Programme 2021-02-052, https://nlnet.nl/assure part
# of Horizon 2020 EU Programme 957073.

from functools import reduce
from operator import xor
import unittest
from nmigen.hdl.ast import (AnyConst, Assert, Signal, Const, unsigned, signed,
                            Mux)
from nmigen.hdl.dsl import Module
from nmutil.formaltest import FHDLTestCase
from nmutil.openpower_sv_bitmanip_in_wiki.clmul import clmul
from nmutil.clmul import BitwiseXorReduce, CLMulAdd
from nmigen.sim import Delay
from nmutil.sim_util import do_sim, hash_256


class TestBitwiseXorReduce(FHDLTestCase):
    def tst(self, input_shapes):
        dut = BitwiseXorReduce(Signal(w, name=f"input_{i}")
                               for i, w in enumerate(input_shapes))
        self.assertEqual(reduce(xor, dut.input_values).shape(),
                         dut.output.shape())

        def case(inputs):
            expected = reduce(xor, inputs)
            with self.subTest(inputs=list(map(hex, inputs)),
                              expected=hex(expected)):
                for i, inp in enumerate(inputs):
                    yield dut.input_values[i].eq(inp)
                yield Delay(1e-6)
                output = yield dut.output
                with self.subTest(output=hex(output)):
                    self.assertEqual(expected, output)

        def process():
            for i in range(100):
                inputs = []
                for inp in dut.input_values:
                    v = hash_256(f"bxorr input {i} {inp.name}")
                    inputs.append(Const.normalize(v, inp.shape()))
                yield from case(inputs)

        with do_sim(self, dut, [*dut.input_values, dut.output]) as sim:
            sim.add_process(process)
            sim.run()

    def tst_formal(self, input_shapes):
        dut = BitwiseXorReduce(Signal(w, name=f"input_{i}")
                               for i, w in enumerate(input_shapes))
        m = Module()
        m.submodules.dut = dut
        for i in dut.input_values:
            m.d.comb += i.eq(AnyConst(i.shape()))
        m.d.comb += Assert(dut.output == reduce(xor, dut.input_values))
        self.assertFormal(m)

    def test_65_of_u64(self):
        self.tst([64] * 65)

    def test_formal_65_of_u64(self):
        self.tst_formal([64] * 65)

    def test_5_of_u6(self):
        self.tst([6] * 5)

    def test_formal_5_of_u6(self):
        self.tst_formal([6] * 5)

    def test_u5_i6_u3_i10(self):
        self.tst([unsigned(5), signed(6), unsigned(3), signed(10)])

    def test_formal_u5_i6_u3_i10(self):
        self.tst_formal([unsigned(5), signed(6), unsigned(3), signed(10)])


class TestCLMulAdd(FHDLTestCase):
    def tst(self, factor_width, terms_width):
        dut = CLMulAdd(factor_width, terms_width)
        self.assertEqual(dut.output.width,
                         max((factor_width * 2 - 1, *terms_width)))

        def case(factor1, factor2, terms):
            expected = reduce(xor, terms, clmul(factor1, factor2))
            with self.subTest(factor1=hex(factor1),
                              factor2=bin(factor2),
                              terms=list(map(hex, terms)),
                              expected=hex(expected)):
                yield dut.factor1.eq(factor1)
                yield dut.factor2.eq(factor2)
                for i, term in enumerate(terms):
                    yield dut.terms[i].eq(term)
                yield Delay(1e-6)
                output = yield dut.output
                with self.subTest(output=hex(output)):
                    self.assertEqual(expected, output)

        def process():
            for i in range(100):
                v = hash_256(f"clmuladd term {i} factor1")
                factor1 = Const.normalize(v, unsigned(factor_width))
                v = hash_256(f"clmuladd term {i} factor2")
                factor2 = Const.normalize(v, unsigned(factor_width))
                terms = []
                for j, term_width in enumerate(terms_width):
                    v = hash_256(f"clmuladd term {i} {j}")
                    terms.append(Const.normalize(v, unsigned(term_width)))
                yield from case(factor1, factor2, terms)
        with do_sim(self, dut, [dut.factor1, dut.factor2, *dut.terms,
                                dut.output]) as sim:
            sim.add_process(process)
            sim.run()

    def test_4x4(self):
        self.tst(4, ())

    def test_4x4_8(self):
        self.tst(4, (8,))

    def test_64x64(self):
        self.tst(64, ())

    def test_64x64_64(self):
        self.tst(64, (64,))

    def test_8x8_16_16_16(self):
        self.tst(8, (16, 16, 16))

    def tst_formal(self, factor_width, terms_width):
        dut = CLMulAdd(factor_width, terms_width)
        m = Module()
        m.submodules.dut = dut
        m.d.comb += dut.factor1.eq(AnyConst(factor_width))
        m.d.comb += dut.factor2.eq(AnyConst(factor_width))
        reduce_inputs = []
        for shift in range(factor_width):
            reduce_inputs.append(
                Mux(dut.factor1[shift], dut.factor2 << shift, 0))
        for i in dut.terms:
            m.d.comb += i.eq(AnyConst(i.shape()))
            reduce_inputs.append(i)
        for i in range(len(reduce_inputs)):
            sig = Signal(reduce_inputs[i].shape(), name=f"reduce_input_{i}")
            m.d.comb += sig.eq(reduce_inputs[i])
            reduce_inputs[i] = sig
        expected = Signal(reduce(xor, reduce_inputs).shape())
        m.d.comb += expected.eq(reduce(xor, reduce_inputs))
        m.d.comb += Assert(dut.output == expected)
        self.assertFormal(m)

    def test_formal_4x4(self):
        self.tst_formal(4, ())

    def test_formal_4x4_8(self):
        self.tst_formal(4, (8,))

    def test_formal_64x64(self):
        self.tst_formal(64, ())

    def test_formal_64x64_64(self):
        self.tst_formal(64, (64,))

    def test_formal_8x8_16_16_16(self):
        self.tst_formal(8, (16, 16, 16))


if __name__ == "__main__":
    unittest.main()
