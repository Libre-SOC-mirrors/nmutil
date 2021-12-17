# SPDX-License-Identifier: LGPL-3-or-later
# See Notices.txt for copyright information

# TODO add funding and explicit copyright notice (contractually required by
# NGI POINTER)

# TODO link to bugreport

from nmigen.hdl.ast import Signal
from nmigen.hdl.dsl import Module
from nmigen.hdl.ir import Elaboratable
from itertools import tee


def pairwise(iterable):
    """
    itertools.pairwise, added in Python 3.10, copied here cuz we support 3.7+
    https://docs.python.org/3.10/library/itertools.html#itertools.pairwise
    """
    # code copied from Python's docs
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)


def grev(input, chunk_sizes, log2_width):
    """
    Python reference implementation of generalized bit-reverse.
    See `GRev` for documentation.
    """
    # mask inputs into range
    input &= 2 ** 2 ** log2_width - 1
    chunk_sizes &= 2 ** log2_width - 1
    # core algorithm:
    retval = 0
    for i in range(2 ** log2_width):
        # don't use `if` so this can be used with nmigen values
        bit = (input & (1 << i)) != 0
        retval |= bit << (i ^ chunk_sizes)
    return retval


class GRev(Elaboratable):
    """ Generalized bit-reverse.

    A generalized bit-reverse is where every output bit is the input bit at
    index `output_bit_index XOR chunk_sizes` where `chunk_sizes` is the
    control input.

    This is useful because many bit/byte reverse operations can be created by
    setting `chunk_sizes` to different values. Some examples for a 64-bit
    `grev` operation:
    * `0b111111` -- reverse bits in the 64-bit word
    * `0b111000` -- reverse bytes in the 64-bit word
    * `0b011000` -- reverse bytes in each 32-bit word independently
    * `0b110000` -- reverse order of 16-bit words

    This is implemented by using a series of `log2_width` 2:1 muxes, this is
    similar, but not identical, to a butterfly network. This is also similar
    to a common barrel-shifter/rotater design.

    The 2:1 muxes are arranged to calculate successive `grev`-ed values where
    each intermediate value's corresponding `chunk_sizes` is progressively
    changed from all zeros to the input `chunk_sizes` by adding one bit at a
    time from the LSB to MSB.

    https://en.wikipedia.org/wiki/Butterfly_network
    https://en.wikipedia.org/wiki/Barrel_shifter#Implementation
    """

    def __init__(self, log2_width):
        self.log2_width = log2_width
        self.width = 1 << log2_width
        self.input = Signal(self.width)
        self.chunk_sizes = Signal(log2_width)
        self.output = Signal(self.width)
        self._steps = [self.input]
        """ internal signals, exposed for unit testing """
        for i in range(1, log2_width):
            self._steps.append(Signal(self.width, name=f"step{i}"))
        self._steps.append(self.output)

    def elaborate(self, platform):
        m = Module()

        # see class doc comment for algorithm docs.
        for i, (step_i, step_o) in enumerate(pairwise(self._steps)):
            chunk_size = 1 << i
            with m.If(self.chunk_sizes[i]):
                for j in range(self.width):
                    m.d.comb += step_o[j].eq(step_i[j ^ chunk_size])
            with m.Else():
                m.d.comb += step_o.eq(step_i)

        return m
