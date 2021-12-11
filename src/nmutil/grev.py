# SPDX-License-Identifier: LGPL-3-or-later
# See Notices.txt for copyright information

# TODO add funding and explicit copyright notice (contractually required by
# NGI POINTER)

from nmigen.hdl.ast import Signal
from nmigen.hdl.dsl import Module
from nmigen.hdl.ir import Elaboratable

# TODO link to bugreport

class GRev(Elaboratable):
    """TODO comments, "this is a half-butterfly aka "generalised reverse"
    so that it shows up in the auto-generated documentation
    link to wikipedia etc. etc. https://en.wikipedia.org/wiki/Butterfly_network

    """

    def __init__(self, log2_width):
        assert isinstance(log2_width, int)
        self.log2_width = log2_width
        self.width = 1 << log2_width

        self.input = Signal(self.width)
        self.chunk_sizes = Signal(log2_width)

        self.output = Signal(self.width)

    def elaborate(self, platform):
        m = Module()

        # XXX internal signals do not need to be members of the module.
        # more to the point: why is the array needed at all?
        def step(i):
            return Signal(self.width, name=f"step{i}")
        _steps = [step(i) for i in range(self.log2_width)]

        for i, step_o in enumerate(_steps):
            step_i = self.input if i == 0 else _steps[i - 1]
            chunk_size = 1 << i
            # TODO comment that this is creating the mux-swapper
            with m.If(self.chunk_sizes[i]):
                # swap path
                for j in range(self.width):
                    # TODO explain what this XOR does
                    m.d.comb += step_o[j].eq(step_i[j ^ chunk_size])
            with m.Else():
                # straight path
                m.d.comb += step_o.eq(step_i)
        # TODO comment that the last "step" is the output
        m.d.comb += self.output.eq(_steps[-1])
        return m
