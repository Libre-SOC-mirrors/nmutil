# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2021 Jacob Lifshay programmerjake@gmail.com
# Copyright (C) 2021 Luke Kenneth Casson Leighton <lkcl@lkcl.net>

# Funded by NLnet Assure Programme 2021-02-052, https://nlnet.nl/assure part
# of Horizon 2020 EU Programme 957073.


"""Generalized bit-reverse. See `GRev` for docs. - no: move the
module docstring here, to describe the Grev concept.
* module docs tell you "about the concept and anything generally useful to know"
* class docs are for "how to actually use the class".
"""

from nmigen.hdl.ast import Signal, Mux, Cat
from nmigen.hdl.ast import Assert
from nmigen.hdl.dsl import Module
from nmigen.hdl.ir import Elaboratable
from nmigen.cli import rtlil


def grev(inval, chunk_sizes, log2_width):
    """XXX start comments here with no space
    Python reference implementation of generalized bit-reverse.
    See `GRev` for documentation.
    """
    # mask inputs into range
    inval &= 2 ** 2 ** log2_width - 1
    chunk_sizes &= 2 ** log2_width - 1
    # core algorithm:
    retval = 0
    for i in range(2 ** log2_width):
        # don't use `if` so this can be used with nmigen values
        bit = (inval & (1 << i)) != 0
        retval |= bit << (i ^ chunk_sizes)
    return retval


class GRev(Elaboratable):
    """Generalized bit-reverse.

    https://bugs.libre-soc.org/show_bug.cgi?id=755

    XXX this is documentation about Grev (the concept) which should be in
    the docstring.  the class string is reserved for describing how to
    *use* the class (describe its inputs and outputs)

    A generalized bit-reverse - also known as a butterfly network - is where
    every output bit is the input bit at index `output_bit_index XOR
    chunk_sizes` where `chunk_sizes` is the control input.

    This is useful because many bit/byte reverse operations can be created by
    setting `chunk_sizes` to different values. Some examples for a 64-bit
    `grev` operation:
    * `0b111111` -- reverse all bits in the 64-bit word
    * `0b111000` -- reverse bytes in the 64-bit word
    * `0b011000` -- reverse bytes in each 32-bit word independently
    * `0b110000` -- reverse order of 16-bit words

    This is implemented by using a series of `log2_width` 2:1 muxes, exactly
    as in a butterfly network: https://en.wikipedia.org/wiki/Butterfly_network

    The 2:1 muxes are arranged to calculate successive `grev`-ed values where
    each intermediate value's corresponding `chunk_sizes` is progressively
    changed from all zeros to the input `chunk_sizes` by adding one bit at a
    time from the LSB to MSB.  (XXX i don't understand this at all!)

    :reverse_order: if True the butterfly steps are performed
                    at offsets of 2^N ... 8 4 2.
                    if False, the order is 2 4 8 ... 2^N
    """

    def __init__(self, log2_width, reverse_order=False):
        self.reverse_order = reverse_order    # reverses the order of steps
        self.log2_width = log2_width
        self.width = 1 << log2_width
        self.input = Signal(self.width)       # XXX mark this as an input
        # XXX is this an input or output?
        self.chunk_sizes = Signal(log2_width)
        self.output = Signal(self.width)      # XXX mark this as the output

    def elaborate(self, platform):
        m = Module()
        comb = m.d.comb

        # accumulate list of internal signals, exposed only for unit testing.
        # contains the input, intermediary steps, and the output.
        self._steps = [self.input]

        # TODO: no. "see class doc comment for algorithm docs." <-- document
        #           *in* the code, not "see another location elsewhere"
        #           (unless it is a repeated text/concept of course, like
        #            with BitwiseLut, and that's because the API is identical)
        #           "see elsewhere" entirely defeats the object of the exercise.
        #           jumping back and forth (page-up, page-down)
        #           between the text and the code splits attention.
        #           the purpose of comments is to be able to understand
        #           (in plain english) the code *at* the point of seeing it
        #           it should contain "the thoughts going through your head"
        #
        #           demonstrated below (with a rewrite)

        step_i = self.input  # start with input as the first step

        # create (reversed?) list of steps
        steps = list(range(self.log2_width))
        if self.reverse_order:
            steps.reverse()

        for i in steps:
            # each chunk is a power-2 jump.
            chunk_size = 1 << i
            # prepare a list of XOR-swapped bits of this layer/step
            butterfly = [step_i[j ^ chunk_size] for j in range(self.width)]
            # create muxes here: 1 bit of chunk_sizes decides swap/no-swap
            step_o = Signal(self.width, name="step%d" % chunk_size)
            comb += step_o.eq(Mux(self.chunk_sizes[i],
                                  Cat(*butterfly), step_i))
            # output becomes input to next layer
            step_i = step_o
            self._steps.append(step_o)  # record steps for test purposes (only)

        # last layer is also the output
        comb += self.output.eq(step_o)

        if platform != 'formal':
            return m

        # formal test comparing directly against the (simpler) version
        m.d.comb += Assert(self.output == grev(self.input,
                                               self.chunk_sizes,
                                               self.log2_width))
        for i, step in enumerate(self._steps):
            cur_chunk_sizes = self.chunk_sizes & (2 ** i - 1)
            step_expected = grev(self.input, cur_chunk_sizes, self.log2_width)
            m.d.comb += Assert(step == step_expected)

        return m

    def ports(self):
        return [self.input, self.chunk_sizes, self.output]


# useful to see what is going on: use yosys "read_ilang test_grev.il; show top"
if __name__ == '__main__':
    dut = GRev(3)
    vl = rtlil.convert(dut, ports=dut.ports())
    with open("test_grev.il", "w") as f:
        f.write(vl)
