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
        assert isinstance(log2_width, int) # TODO: remove. unnecessary.
        self.log2_width = log2_width
        self.width = 1 << log2_width

        self.input = Signal(self.width)
        self.chunk_sizes = Signal(log2_width)

        self.output = Signal(self.width)

    def elaborate(self, platform):
        m = Module()

        _steps = [] # cumulative list of steps (for unit test purposes only)

        step_i = self.input # start combinatorial chain with the input

        # TODO: comment that this creates a full combinatorial chain
        # of RADIX-2 butterfly-network "swappers"
        for i, step_o in enumerate(_steps):
            step_o = Signal(self.width, name="step_%d" % i)
            _steps.append(step_o)
            # TODO explain that chunk swap-sizes jump by a power2 each time
            chunk_size = 1 << i
            # TODO comment that this is creating the mux-swapper
            with m.If(self.chunk_sizes[i]):
                # the mux swap path
                for j in range(self.width):
                    # TODO explain what this XOR does
                    m.d.comb += step_o[j].eq(step_i[j ^ chunk_size])
            with m.Else():
                # the mux straight path
                m.d.comb += step_o.eq(step_i)
            step_i = step_o # for next loop, to create the combinatorial chain
        # TODO comment that the last "step" is the output
        m.d.comb += self.output.eq(_steps[-1]) # TODO: replace with step_o

        # give access to the steps list for testing purposes
        self._steps = _steps

        return m
