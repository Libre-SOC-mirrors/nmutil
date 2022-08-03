# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2022 Jacob Lifshay

import unittest
from nmigen.hdl.ast import AnyConst, Assert, Signal, Const
from nmigen.hdl.dsl import Module
from nmutil.formaltest import FHDLTestCase
from nmutil.picker import PriorityPicker, MultiPriorityPicker


class TestPriorityPicker(FHDLTestCase):
    def tst(self, wid, msb_mode, reverse_i, reverse_o):
        assert isinstance(wid, int)
        assert isinstance(msb_mode, bool)
        assert isinstance(reverse_i, bool)
        assert isinstance(reverse_o, bool)
        dut = PriorityPicker(wid=wid, msb_mode=msb_mode, reverse_i=reverse_i,
                             reverse_o=reverse_o)
        self.assertEqual(wid, dut.wid)
        self.assertEqual(msb_mode, dut.msb_mode)
        self.assertEqual(reverse_i, dut.reverse_i)
        self.assertEqual(reverse_o, dut.reverse_o)
        self.assertEqual(len(dut.i), wid)
        self.assertEqual(len(dut.o), wid)
        self.assertEqual(len(dut.en_o), 1)
        m = Module()
        m.submodules.dut = dut
        m.d.comb += dut.i.eq(AnyConst(wid))

        # assert dut.o only has zero or one bit set
        m.d.comb += Assert((dut.o & (dut.o - 1)) == 0)

        m.d.comb += Assert((dut.o != 0) == dut.en_o)

        unreversed_i = Signal(wid)
        if reverse_i:
            m.d.comb += unreversed_i.eq(dut.i[::-1])
        else:
            m.d.comb += unreversed_i.eq(dut.i)

        unreversed_o = Signal(wid)
        if reverse_o:
            m.d.comb += unreversed_o.eq(dut.o[::-1])
        else:
            m.d.comb += unreversed_o.eq(dut.o)

        expected_unreversed_o = Signal(wid)

        found = Const(False, 1)
        for i in reversed(range(wid)) if msb_mode else range(wid):
            m.d.comb += expected_unreversed_o[i].eq(unreversed_i[i] & ~found)
            found |= unreversed_i[i]

        m.d.comb += Assert(expected_unreversed_o == unreversed_o)

        self.assertFormal(m)

    def test_1_msbm_f_revi_f_revo_f(self):
        self.tst(wid=1, msb_mode=False, reverse_i=False, reverse_o=False)

    def test_1_msbm_f_revi_f_revo_t(self):
        self.tst(wid=1, msb_mode=False, reverse_i=False, reverse_o=True)

    def test_1_msbm_f_revi_t_revo_f(self):
        self.tst(wid=1, msb_mode=False, reverse_i=True, reverse_o=False)

    def test_1_msbm_f_revi_t_revo_t(self):
        self.tst(wid=1, msb_mode=False, reverse_i=True, reverse_o=True)

    def test_1_msbm_t_revi_f_revo_f(self):
        self.tst(wid=1, msb_mode=True, reverse_i=False, reverse_o=False)

    def test_1_msbm_t_revi_f_revo_t(self):
        self.tst(wid=1, msb_mode=True, reverse_i=False, reverse_o=True)

    def test_1_msbm_t_revi_t_revo_f(self):
        self.tst(wid=1, msb_mode=True, reverse_i=True, reverse_o=False)

    def test_1_msbm_t_revi_t_revo_t(self):
        self.tst(wid=1, msb_mode=True, reverse_i=True, reverse_o=True)

    def test_2_msbm_f_revi_f_revo_f(self):
        self.tst(wid=2, msb_mode=False, reverse_i=False, reverse_o=False)

    def test_2_msbm_f_revi_f_revo_t(self):
        self.tst(wid=2, msb_mode=False, reverse_i=False, reverse_o=True)

    def test_2_msbm_f_revi_t_revo_f(self):
        self.tst(wid=2, msb_mode=False, reverse_i=True, reverse_o=False)

    def test_2_msbm_f_revi_t_revo_t(self):
        self.tst(wid=2, msb_mode=False, reverse_i=True, reverse_o=True)

    def test_2_msbm_t_revi_f_revo_f(self):
        self.tst(wid=2, msb_mode=True, reverse_i=False, reverse_o=False)

    def test_2_msbm_t_revi_f_revo_t(self):
        self.tst(wid=2, msb_mode=True, reverse_i=False, reverse_o=True)

    def test_2_msbm_t_revi_t_revo_f(self):
        self.tst(wid=2, msb_mode=True, reverse_i=True, reverse_o=False)

    def test_2_msbm_t_revi_t_revo_t(self):
        self.tst(wid=2, msb_mode=True, reverse_i=True, reverse_o=True)

    def test_3_msbm_f_revi_f_revo_f(self):
        self.tst(wid=3, msb_mode=False, reverse_i=False, reverse_o=False)

    def test_3_msbm_f_revi_f_revo_t(self):
        self.tst(wid=3, msb_mode=False, reverse_i=False, reverse_o=True)

    def test_3_msbm_f_revi_t_revo_f(self):
        self.tst(wid=3, msb_mode=False, reverse_i=True, reverse_o=False)

    def test_3_msbm_f_revi_t_revo_t(self):
        self.tst(wid=3, msb_mode=False, reverse_i=True, reverse_o=True)

    def test_3_msbm_t_revi_f_revo_f(self):
        self.tst(wid=3, msb_mode=True, reverse_i=False, reverse_o=False)

    def test_3_msbm_t_revi_f_revo_t(self):
        self.tst(wid=3, msb_mode=True, reverse_i=False, reverse_o=True)

    def test_3_msbm_t_revi_t_revo_f(self):
        self.tst(wid=3, msb_mode=True, reverse_i=True, reverse_o=False)

    def test_3_msbm_t_revi_t_revo_t(self):
        self.tst(wid=3, msb_mode=True, reverse_i=True, reverse_o=True)

    def test_4_msbm_f_revi_f_revo_f(self):
        self.tst(wid=4, msb_mode=False, reverse_i=False, reverse_o=False)

    def test_4_msbm_f_revi_f_revo_t(self):
        self.tst(wid=4, msb_mode=False, reverse_i=False, reverse_o=True)

    def test_4_msbm_f_revi_t_revo_f(self):
        self.tst(wid=4, msb_mode=False, reverse_i=True, reverse_o=False)

    def test_4_msbm_f_revi_t_revo_t(self):
        self.tst(wid=4, msb_mode=False, reverse_i=True, reverse_o=True)

    def test_4_msbm_t_revi_f_revo_f(self):
        self.tst(wid=4, msb_mode=True, reverse_i=False, reverse_o=False)

    def test_4_msbm_t_revi_f_revo_t(self):
        self.tst(wid=4, msb_mode=True, reverse_i=False, reverse_o=True)

    def test_4_msbm_t_revi_t_revo_f(self):
        self.tst(wid=4, msb_mode=True, reverse_i=True, reverse_o=False)

    def test_4_msbm_t_revi_t_revo_t(self):
        self.tst(wid=4, msb_mode=True, reverse_i=True, reverse_o=True)

    def test_8_msbm_f_revi_f_revo_f(self):
        self.tst(wid=8, msb_mode=False, reverse_i=False, reverse_o=False)

    def test_8_msbm_f_revi_f_revo_t(self):
        self.tst(wid=8, msb_mode=False, reverse_i=False, reverse_o=True)

    def test_8_msbm_f_revi_t_revo_f(self):
        self.tst(wid=8, msb_mode=False, reverse_i=True, reverse_o=False)

    def test_8_msbm_f_revi_t_revo_t(self):
        self.tst(wid=8, msb_mode=False, reverse_i=True, reverse_o=True)

    def test_8_msbm_t_revi_f_revo_f(self):
        self.tst(wid=8, msb_mode=True, reverse_i=False, reverse_o=False)

    def test_8_msbm_t_revi_f_revo_t(self):
        self.tst(wid=8, msb_mode=True, reverse_i=False, reverse_o=True)

    def test_8_msbm_t_revi_t_revo_f(self):
        self.tst(wid=8, msb_mode=True, reverse_i=True, reverse_o=False)

    def test_8_msbm_t_revi_t_revo_t(self):
        self.tst(wid=8, msb_mode=True, reverse_i=True, reverse_o=True)

    def test_32_msbm_f_revi_f_revo_f(self):
        self.tst(wid=32, msb_mode=False, reverse_i=False, reverse_o=False)

    def test_32_msbm_f_revi_f_revo_t(self):
        self.tst(wid=32, msb_mode=False, reverse_i=False, reverse_o=True)

    def test_32_msbm_f_revi_t_revo_f(self):
        self.tst(wid=32, msb_mode=False, reverse_i=True, reverse_o=False)

    def test_32_msbm_f_revi_t_revo_t(self):
        self.tst(wid=32, msb_mode=False, reverse_i=True, reverse_o=True)

    def test_32_msbm_t_revi_f_revo_f(self):
        self.tst(wid=32, msb_mode=True, reverse_i=False, reverse_o=False)

    def test_32_msbm_t_revi_f_revo_t(self):
        self.tst(wid=32, msb_mode=True, reverse_i=False, reverse_o=True)

    def test_32_msbm_t_revi_t_revo_f(self):
        self.tst(wid=32, msb_mode=True, reverse_i=True, reverse_o=False)

    def test_32_msbm_t_revi_t_revo_t(self):
        self.tst(wid=32, msb_mode=True, reverse_i=True, reverse_o=True)

    def test_64_msbm_f_revi_f_revo_f(self):
        self.tst(wid=64, msb_mode=False, reverse_i=False, reverse_o=False)

    def test_64_msbm_f_revi_f_revo_t(self):
        self.tst(wid=64, msb_mode=False, reverse_i=False, reverse_o=True)

    def test_64_msbm_f_revi_t_revo_f(self):
        self.tst(wid=64, msb_mode=False, reverse_i=True, reverse_o=False)

    def test_64_msbm_f_revi_t_revo_t(self):
        self.tst(wid=64, msb_mode=False, reverse_i=True, reverse_o=True)

    def test_64_msbm_t_revi_f_revo_f(self):
        self.tst(wid=64, msb_mode=True, reverse_i=False, reverse_o=False)

    def test_64_msbm_t_revi_f_revo_t(self):
        self.tst(wid=64, msb_mode=True, reverse_i=False, reverse_o=True)

    def test_64_msbm_t_revi_t_revo_f(self):
        self.tst(wid=64, msb_mode=True, reverse_i=True, reverse_o=False)

    def test_64_msbm_t_revi_t_revo_t(self):
        self.tst(wid=64, msb_mode=True, reverse_i=True, reverse_o=True)


if __name__ == "__main__":
    unittest.main()
