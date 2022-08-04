# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2022 Jacob Lifshay

from functools import reduce
import operator
import unittest
from nmigen.hdl.ast import AnyConst, Assert, Signal, Const, Array, Shape, Mux
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


class TestMultiPriorityPicker(FHDLTestCase):
    def tst(self, *, cls=MultiPriorityPicker, wid, levels, indices, multi_in):
        assert isinstance(wid, int) and wid >= 1
        assert isinstance(levels, int) and 1 <= levels <= wid
        assert isinstance(indices, bool)
        assert isinstance(multi_in, bool)
        dut = cls(wid=wid, levels=levels, indices=indices, multi_in=multi_in)
        self.assertEqual(wid, dut.wid)
        self.assertEqual(levels, dut.levels)
        self.assertEqual(indices, dut.indices)
        self.assertEqual(multi_in, dut.multi_in)
        expected_ports = []
        if multi_in:
            self.assertIsInstance(dut.i, Array)
            self.assertEqual(len(dut.i), levels)
            for i in dut.i:
                self.assertIsInstance(i, Signal)
                self.assertEqual(len(i), wid)
                expected_ports.append(i)
        else:
            self.assertIsInstance(dut.i, Signal)
            self.assertEqual(len(dut.i), wid)
            expected_ports.append(dut.i)

        self.assertIsInstance(dut.o, Array)
        self.assertEqual(len(dut.o), levels)
        for o in dut.o:
            self.assertIsInstance(o, Signal)
            self.assertEqual(len(o), wid)
            expected_ports.append(o)

        self.assertEqual(len(dut.en_o), levels)
        expected_ports.append(dut.en_o)

        if indices:
            expected_idx_o_shape = Shape.cast(range(levels))
            if levels <= 1:
                expected_idx_o_shape = Shape(0, False)
            self.assertIsInstance(dut.idx_o, Array)
            self.assertEqual(len(dut.idx_o), levels)
            for idx_o in dut.idx_o:
                self.assertIsInstance(idx_o, Signal)
                self.assertEqual(idx_o.shape(), expected_idx_o_shape)
                expected_ports.append(idx_o)
        else:
            self.assertFalse(hasattr(dut, "idx_o"))

        self.assertListEqual(expected_ports, dut.ports())

        m = Module()
        m.submodules.dut = dut
        if multi_in:
            for i in dut.i:
                m.d.comb += i.eq(AnyConst(wid))
        else:
            m.d.comb += dut.i.eq(AnyConst(wid))

        prev_set = 0
        for o, en_o in zip(dut.o, dut.en_o):
            # assert o only has zero or one bit set
            m.d.comb += Assert((o & (o - 1)) == 0)
            # assert o doesn't overlap any previous outputs
            m.d.comb += Assert((o & prev_set) == 0)
            prev_set |= o

            m.d.comb += Assert((o != 0) == en_o)

        prev_set = Const(0, wid)
        priority_pickers = [PriorityPicker(wid) for _ in range(levels)]
        for level in range(levels):
            pp = priority_pickers[level]
            setattr(m.submodules, f"pp_{level}", pp)
            inp = dut.i[level] if multi_in else dut.i
            m.d.comb += pp.i.eq(inp & ~prev_set)
            cur_set = Signal(wid, name=f"cur_set_{level}")
            m.d.comb += cur_set.eq(prev_set | pp.o)
            prev_set = cur_set
            m.d.comb += Assert(pp.o == dut.o[level])
            expected_idx = Signal(32, name=f"expected_idx_{level}")
            number_of_prev_en_o_set = reduce(
                operator.add, (i.en_o for i in priority_pickers[:level]), 0)
            m.d.comb += expected_idx.eq(number_of_prev_en_o_set)
            if indices:
                m.d.comb += Assert(expected_idx == dut.idx_o[level])

        self.assertFormal(m)

    def test_4_levels_1_idxs_f_mi_f(self):
        self.tst(wid=4, levels=1, indices=False, multi_in=False)

    def test_4_levels_1_idxs_f_mi_t(self):
        self.tst(wid=4, levels=1, indices=False, multi_in=True)

    def test_4_levels_1_idxs_t_mi_f(self):
        self.tst(wid=4, levels=1, indices=True, multi_in=False)

    def test_4_levels_1_idxs_t_mi_t(self):
        self.tst(wid=4, levels=1, indices=True, multi_in=True)

    def test_4_levels_2_idxs_f_mi_f(self):
        self.tst(wid=4, levels=2, indices=False, multi_in=False)

    def test_4_levels_2_idxs_f_mi_t(self):
        self.tst(wid=4, levels=2, indices=False, multi_in=True)

    def test_4_levels_2_idxs_t_mi_f(self):
        self.tst(wid=4, levels=2, indices=True, multi_in=False)

    def test_4_levels_2_idxs_t_mi_t(self):
        self.tst(wid=4, levels=2, indices=True, multi_in=True)

    def test_4_levels_3_idxs_f_mi_f(self):
        self.tst(wid=4, levels=3, indices=False, multi_in=False)

    def test_4_levels_3_idxs_f_mi_t(self):
        self.tst(wid=4, levels=3, indices=False, multi_in=True)

    def test_4_levels_3_idxs_t_mi_f(self):
        self.tst(wid=4, levels=3, indices=True, multi_in=False)

    def test_4_levels_3_idxs_t_mi_t(self):
        self.tst(wid=4, levels=3, indices=True, multi_in=True)

    def test_4_levels_4_idxs_f_mi_f(self):
        self.tst(wid=4, levels=4, indices=False, multi_in=False)

    def test_4_levels_4_idxs_f_mi_t(self):
        self.tst(wid=4, levels=4, indices=False, multi_in=True)

    def test_4_levels_4_idxs_t_mi_f(self):
        self.tst(wid=4, levels=4, indices=True, multi_in=False)

    def test_4_levels_4_idxs_t_mi_t(self):
        self.tst(wid=4, levels=4, indices=True, multi_in=True)

    def test_8_levels_1_idxs_f_mi_f(self):
        self.tst(wid=8, levels=1, indices=False, multi_in=False)

    def test_8_levels_1_idxs_f_mi_t(self):
        self.tst(wid=8, levels=1, indices=False, multi_in=True)

    def test_8_levels_1_idxs_t_mi_f(self):
        self.tst(wid=8, levels=1, indices=True, multi_in=False)

    def test_8_levels_1_idxs_t_mi_t(self):
        self.tst(wid=8, levels=1, indices=True, multi_in=True)

    def test_8_levels_2_idxs_f_mi_f(self):
        self.tst(wid=8, levels=2, indices=False, multi_in=False)

    def test_8_levels_2_idxs_f_mi_t(self):
        self.tst(wid=8, levels=2, indices=False, multi_in=True)

    def test_8_levels_2_idxs_t_mi_f(self):
        self.tst(wid=8, levels=2, indices=True, multi_in=False)

    def test_8_levels_2_idxs_t_mi_t(self):
        self.tst(wid=8, levels=2, indices=True, multi_in=True)

    def test_8_levels_3_idxs_f_mi_f(self):
        self.tst(wid=8, levels=3, indices=False, multi_in=False)

    def test_8_levels_3_idxs_f_mi_t(self):
        self.tst(wid=8, levels=3, indices=False, multi_in=True)

    def test_8_levels_3_idxs_t_mi_f(self):
        self.tst(wid=8, levels=3, indices=True, multi_in=False)

    def test_8_levels_3_idxs_t_mi_t(self):
        self.tst(wid=8, levels=3, indices=True, multi_in=True)

    def test_8_levels_4_idxs_f_mi_f(self):
        self.tst(wid=8, levels=4, indices=False, multi_in=False)

    def test_8_levels_4_idxs_f_mi_t(self):
        self.tst(wid=8, levels=4, indices=False, multi_in=True)

    def test_8_levels_4_idxs_t_mi_f(self):
        self.tst(wid=8, levels=4, indices=True, multi_in=False)

    def test_8_levels_4_idxs_t_mi_t(self):
        self.tst(wid=8, levels=4, indices=True, multi_in=True)

    def test_8_levels_5_idxs_f_mi_f(self):
        self.tst(wid=8, levels=5, indices=False, multi_in=False)

    def test_8_levels_5_idxs_f_mi_t(self):
        self.tst(wid=8, levels=5, indices=False, multi_in=True)

    def test_8_levels_5_idxs_t_mi_f(self):
        self.tst(wid=8, levels=5, indices=True, multi_in=False)

    def test_8_levels_5_idxs_t_mi_t(self):
        self.tst(wid=8, levels=5, indices=True, multi_in=True)

    def test_8_levels_6_idxs_f_mi_f(self):
        self.tst(wid=8, levels=6, indices=False, multi_in=False)

    def test_8_levels_6_idxs_f_mi_t(self):
        self.tst(wid=8, levels=6, indices=False, multi_in=True)

    def test_8_levels_6_idxs_t_mi_f(self):
        self.tst(wid=8, levels=6, indices=True, multi_in=False)

    def test_8_levels_6_idxs_t_mi_t(self):
        self.tst(wid=8, levels=6, indices=True, multi_in=True)

    def test_8_levels_7_idxs_f_mi_f(self):
        self.tst(wid=8, levels=7, indices=False, multi_in=False)

    def test_8_levels_7_idxs_f_mi_t(self):
        self.tst(wid=8, levels=7, indices=False, multi_in=True)

    def test_8_levels_7_idxs_t_mi_f(self):
        self.tst(wid=8, levels=7, indices=True, multi_in=False)

    def test_8_levels_7_idxs_t_mi_t(self):
        self.tst(wid=8, levels=7, indices=True, multi_in=True)

    def test_8_levels_8_idxs_f_mi_f(self):
        self.tst(wid=8, levels=8, indices=False, multi_in=False)

    def test_8_levels_8_idxs_f_mi_t(self):
        self.tst(wid=8, levels=8, indices=False, multi_in=True)

    def test_8_levels_8_idxs_t_mi_f(self):
        self.tst(wid=8, levels=8, indices=True, multi_in=False)

    def test_8_levels_8_idxs_t_mi_t(self):
        self.tst(wid=8, levels=8, indices=True, multi_in=True)


if __name__ == "__main__":
    unittest.main()
