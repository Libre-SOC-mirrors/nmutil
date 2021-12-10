# SPDX-License-Identifier: LGPL-3-or-later
# See Notices.txt for copyright information

from nmigen.hdl.ast import Signal
from nmigen.hdl.dsl import Module
from nmigen.hdl.ir import Elaboratable


class GRev(Elaboratable):
    def __init__(self, log2_width):
        assert isinstance(log2_width, int)
        self.log2_width = log2_width
        self.width = 1 << log2_width

        self.input = Signal(self.width)
        self.chunk_sizes = Signal(log2_width)

        def step(i):
            return Signal(self.width, name=f"step{i}")
        self._steps = [step(i) for i in range(log2_width)]

        self.output = Signal(self.width)

    def elaborate(self, platform):
        m = Module()
        for i, step_o in enumerate(self._steps):
            step_i = self.input if i == 0 else self._steps[i - 1]
            chunk_size = 1 << i
            with m.If(self.chunk_sizes[i]):
                for j in range(self.width):
                    m.d.comb += step_o[j].eq(step_i[j ^ chunk_size])
            with m.Else():
                m.d.comb += step_o.eq(step_i)
        m.d.comb += self.output.eq(self._steps[-1])
        return m
