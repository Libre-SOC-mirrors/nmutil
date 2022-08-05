# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2022 Jacob Lifshay

import unittest
from nmigen.hdl.ast import (AnySeq, Assert, Signal, Assume, Const,
                            unsigned, AnyConst)
from nmigen.hdl.dsl import Module
from nmutil.formaltest import FHDLTestCase
from nmutil.queue import Queue
from nmutil.sim_util import write_il


class TestQueue(FHDLTestCase):
    def tst(self, width, depth, fwft, pipe):
        assert isinstance(width, int)
        assert isinstance(depth, int)
        assert isinstance(fwft, bool)
        assert isinstance(pipe, bool)
        dut = Queue(width=width, depth=depth, fwft=fwft, pipe=pipe)
        self.assertEqual(width, dut.width)
        self.assertEqual(depth, dut.depth)
        self.assertEqual(fwft, dut.fwft)
        self.assertEqual(pipe, dut.pipe)
        write_il(self, dut, ports=[
            dut.level,
            dut.r_data, dut.r_en, dut.r_rdy,
            dut.w_data, dut.w_en, dut.w_rdy,
        ])
        m = Module()
        m.submodules.dut = dut
        m.d.comb += dut.r_en.eq(AnySeq(1))
        m.d.comb += dut.w_data.eq(AnySeq(width))
        m.d.comb += dut.w_en.eq(AnySeq(1))

        index_width = 16
        max_index = Const(-1, unsigned(index_width))

        check_r_data = Signal(width)
        check_r_data_valid = Signal(reset=False)
        r_index = Signal(index_width)
        check_w_data = Signal(width)
        check_w_data_valid = Signal(reset=False)
        w_index = Signal(index_width)
        check_index = Signal(index_width)
        m.d.comb += check_index.eq(AnyConst(index_width))

        with m.If(dut.r_en & dut.r_rdy):
            with m.If(r_index == check_index):
                m.d.sync += [
                    check_r_data.eq(dut.r_data),
                    check_r_data_valid.eq(True),
                ]
            m.d.sync += [
                Assume(r_index != max_index),
                r_index.eq(r_index + 1),
            ]

        with m.If(dut.w_en & dut.w_rdy):
            with m.If(w_index == check_index):
                m.d.sync += [
                    check_w_data.eq(dut.w_data),
                    check_w_data_valid.eq(True),
                ]
            m.d.sync += [
                Assume(w_index != max_index),
                w_index.eq(w_index + 1),
            ]

        with m.If(check_r_data_valid & check_w_data_valid):
            m.d.comb += Assert(check_r_data == check_w_data)

        # 10 is enough to fully test smaller depth queues, larger queues are
        # assumed to be correct because the logic doesn't really depend on
        # queue depth past the first few values.
        self.assertFormal(m, depth=10)

    def test_have_all(self):
        def bool_char(v):
            if v:
                return "t"
            return "f"

        missing = []

        for width in [1, 8]:
            for depth in range(8 + 1):
                for fwft in (False, True):
                    for pipe in (False, True):
                        name = (f"test_{width}_"
                                f"depth_{depth}_"
                                f"fwft_{bool_char(fwft)}_"
                                f"pipe_{bool_char(pipe)}")
                        if not callable(getattr(self, name, None)):
                            missing.append(f"    def {name}(self):\n"
                                           f"        self.tst("
                                           f"width={width}, depth={depth}, "
                                           f"fwft={fwft}, pipe={pipe})\n")
        missing = "\n".join(missing)
        self.assertTrue(missing == "", f"missing functions:\n\n{missing}")

    def test_1_depth_0_fwft_f_pipe_f(self):
        self.tst(width=1, depth=0, fwft=False, pipe=False)

    def test_1_depth_0_fwft_f_pipe_t(self):
        self.tst(width=1, depth=0, fwft=False, pipe=True)

    def test_1_depth_0_fwft_t_pipe_f(self):
        self.tst(width=1, depth=0, fwft=True, pipe=False)

    def test_1_depth_0_fwft_t_pipe_t(self):
        self.tst(width=1, depth=0, fwft=True, pipe=True)

    def test_1_depth_1_fwft_f_pipe_f(self):
        self.tst(width=1, depth=1, fwft=False, pipe=False)

    def test_1_depth_1_fwft_f_pipe_t(self):
        self.tst(width=1, depth=1, fwft=False, pipe=True)

    def test_1_depth_1_fwft_t_pipe_f(self):
        self.tst(width=1, depth=1, fwft=True, pipe=False)

    def test_1_depth_1_fwft_t_pipe_t(self):
        self.tst(width=1, depth=1, fwft=True, pipe=True)

    def test_1_depth_2_fwft_f_pipe_f(self):
        self.tst(width=1, depth=2, fwft=False, pipe=False)

    def test_1_depth_2_fwft_f_pipe_t(self):
        self.tst(width=1, depth=2, fwft=False, pipe=True)

    def test_1_depth_2_fwft_t_pipe_f(self):
        self.tst(width=1, depth=2, fwft=True, pipe=False)

    def test_1_depth_2_fwft_t_pipe_t(self):
        self.tst(width=1, depth=2, fwft=True, pipe=True)

    def test_1_depth_3_fwft_f_pipe_f(self):
        self.tst(width=1, depth=3, fwft=False, pipe=False)

    def test_1_depth_3_fwft_f_pipe_t(self):
        self.tst(width=1, depth=3, fwft=False, pipe=True)

    def test_1_depth_3_fwft_t_pipe_f(self):
        self.tst(width=1, depth=3, fwft=True, pipe=False)

    def test_1_depth_3_fwft_t_pipe_t(self):
        self.tst(width=1, depth=3, fwft=True, pipe=True)

    def test_1_depth_4_fwft_f_pipe_f(self):
        self.tst(width=1, depth=4, fwft=False, pipe=False)

    def test_1_depth_4_fwft_f_pipe_t(self):
        self.tst(width=1, depth=4, fwft=False, pipe=True)

    def test_1_depth_4_fwft_t_pipe_f(self):
        self.tst(width=1, depth=4, fwft=True, pipe=False)

    def test_1_depth_4_fwft_t_pipe_t(self):
        self.tst(width=1, depth=4, fwft=True, pipe=True)

    def test_1_depth_5_fwft_f_pipe_f(self):
        self.tst(width=1, depth=5, fwft=False, pipe=False)

    def test_1_depth_5_fwft_f_pipe_t(self):
        self.tst(width=1, depth=5, fwft=False, pipe=True)

    def test_1_depth_5_fwft_t_pipe_f(self):
        self.tst(width=1, depth=5, fwft=True, pipe=False)

    def test_1_depth_5_fwft_t_pipe_t(self):
        self.tst(width=1, depth=5, fwft=True, pipe=True)

    def test_1_depth_6_fwft_f_pipe_f(self):
        self.tst(width=1, depth=6, fwft=False, pipe=False)

    def test_1_depth_6_fwft_f_pipe_t(self):
        self.tst(width=1, depth=6, fwft=False, pipe=True)

    def test_1_depth_6_fwft_t_pipe_f(self):
        self.tst(width=1, depth=6, fwft=True, pipe=False)

    def test_1_depth_6_fwft_t_pipe_t(self):
        self.tst(width=1, depth=6, fwft=True, pipe=True)

    def test_1_depth_7_fwft_f_pipe_f(self):
        self.tst(width=1, depth=7, fwft=False, pipe=False)

    def test_1_depth_7_fwft_f_pipe_t(self):
        self.tst(width=1, depth=7, fwft=False, pipe=True)

    def test_1_depth_7_fwft_t_pipe_f(self):
        self.tst(width=1, depth=7, fwft=True, pipe=False)

    def test_1_depth_7_fwft_t_pipe_t(self):
        self.tst(width=1, depth=7, fwft=True, pipe=True)

    def test_1_depth_8_fwft_f_pipe_f(self):
        self.tst(width=1, depth=8, fwft=False, pipe=False)

    def test_1_depth_8_fwft_f_pipe_t(self):
        self.tst(width=1, depth=8, fwft=False, pipe=True)

    def test_1_depth_8_fwft_t_pipe_f(self):
        self.tst(width=1, depth=8, fwft=True, pipe=False)

    def test_1_depth_8_fwft_t_pipe_t(self):
        self.tst(width=1, depth=8, fwft=True, pipe=True)

    def test_8_depth_0_fwft_f_pipe_f(self):
        self.tst(width=8, depth=0, fwft=False, pipe=False)

    def test_8_depth_0_fwft_f_pipe_t(self):
        self.tst(width=8, depth=0, fwft=False, pipe=True)

    def test_8_depth_0_fwft_t_pipe_f(self):
        self.tst(width=8, depth=0, fwft=True, pipe=False)

    def test_8_depth_0_fwft_t_pipe_t(self):
        self.tst(width=8, depth=0, fwft=True, pipe=True)

    def test_8_depth_1_fwft_f_pipe_f(self):
        self.tst(width=8, depth=1, fwft=False, pipe=False)

    def test_8_depth_1_fwft_f_pipe_t(self):
        self.tst(width=8, depth=1, fwft=False, pipe=True)

    def test_8_depth_1_fwft_t_pipe_f(self):
        self.tst(width=8, depth=1, fwft=True, pipe=False)

    def test_8_depth_1_fwft_t_pipe_t(self):
        self.tst(width=8, depth=1, fwft=True, pipe=True)

    def test_8_depth_2_fwft_f_pipe_f(self):
        self.tst(width=8, depth=2, fwft=False, pipe=False)

    def test_8_depth_2_fwft_f_pipe_t(self):
        self.tst(width=8, depth=2, fwft=False, pipe=True)

    def test_8_depth_2_fwft_t_pipe_f(self):
        self.tst(width=8, depth=2, fwft=True, pipe=False)

    def test_8_depth_2_fwft_t_pipe_t(self):
        self.tst(width=8, depth=2, fwft=True, pipe=True)

    def test_8_depth_3_fwft_f_pipe_f(self):
        self.tst(width=8, depth=3, fwft=False, pipe=False)

    def test_8_depth_3_fwft_f_pipe_t(self):
        self.tst(width=8, depth=3, fwft=False, pipe=True)

    def test_8_depth_3_fwft_t_pipe_f(self):
        self.tst(width=8, depth=3, fwft=True, pipe=False)

    def test_8_depth_3_fwft_t_pipe_t(self):
        self.tst(width=8, depth=3, fwft=True, pipe=True)

    def test_8_depth_4_fwft_f_pipe_f(self):
        self.tst(width=8, depth=4, fwft=False, pipe=False)

    def test_8_depth_4_fwft_f_pipe_t(self):
        self.tst(width=8, depth=4, fwft=False, pipe=True)

    def test_8_depth_4_fwft_t_pipe_f(self):
        self.tst(width=8, depth=4, fwft=True, pipe=False)

    def test_8_depth_4_fwft_t_pipe_t(self):
        self.tst(width=8, depth=4, fwft=True, pipe=True)

    def test_8_depth_5_fwft_f_pipe_f(self):
        self.tst(width=8, depth=5, fwft=False, pipe=False)

    def test_8_depth_5_fwft_f_pipe_t(self):
        self.tst(width=8, depth=5, fwft=False, pipe=True)

    def test_8_depth_5_fwft_t_pipe_f(self):
        self.tst(width=8, depth=5, fwft=True, pipe=False)

    def test_8_depth_5_fwft_t_pipe_t(self):
        self.tst(width=8, depth=5, fwft=True, pipe=True)

    def test_8_depth_6_fwft_f_pipe_f(self):
        self.tst(width=8, depth=6, fwft=False, pipe=False)

    def test_8_depth_6_fwft_f_pipe_t(self):
        self.tst(width=8, depth=6, fwft=False, pipe=True)

    def test_8_depth_6_fwft_t_pipe_f(self):
        self.tst(width=8, depth=6, fwft=True, pipe=False)

    def test_8_depth_6_fwft_t_pipe_t(self):
        self.tst(width=8, depth=6, fwft=True, pipe=True)

    def test_8_depth_7_fwft_f_pipe_f(self):
        self.tst(width=8, depth=7, fwft=False, pipe=False)

    def test_8_depth_7_fwft_f_pipe_t(self):
        self.tst(width=8, depth=7, fwft=False, pipe=True)

    def test_8_depth_7_fwft_t_pipe_f(self):
        self.tst(width=8, depth=7, fwft=True, pipe=False)

    def test_8_depth_7_fwft_t_pipe_t(self):
        self.tst(width=8, depth=7, fwft=True, pipe=True)

    def test_8_depth_8_fwft_f_pipe_f(self):
        self.tst(width=8, depth=8, fwft=False, pipe=False)

    def test_8_depth_8_fwft_f_pipe_t(self):
        self.tst(width=8, depth=8, fwft=False, pipe=True)

    def test_8_depth_8_fwft_t_pipe_f(self):
        self.tst(width=8, depth=8, fwft=True, pipe=False)

    def test_8_depth_8_fwft_t_pipe_t(self):
        self.tst(width=8, depth=8, fwft=True, pipe=True)


if __name__ == "__main__":
    unittest.main()
