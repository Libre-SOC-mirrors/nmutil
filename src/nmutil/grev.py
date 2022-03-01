# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2021 Jacob Lifshay programmerjake@gmail.com
# Copyright (C) 2021 Luke Kenneth Casson Leighton <lkcl@lkcl.net>

# Funded by NLnet Assure Programme 2021-02-052, https://nlnet.nl/assure part
# of Horizon 2020 EU Programme 957073.

r"""Generalized bit-reverse.

https://bugs.libre-soc.org/show_bug.cgi?id=755

A generalized bit-reverse is the following operation:
grev(input, chunk_sizes):
    for i in range(input.width):
        j = i XOR chunk_sizes
        output bit i = input bit j
    return output

This is useful because many bit/byte reverse operations can be created by
setting `chunk_sizes` to different values. Some examples for a 64-bit
`grev` operation:
* `0b111111` -- reverse all bits in the 64-bit word
* `0b111000` -- reverse bytes in the 64-bit word
* `0b011000` -- reverse bytes in each 32-bit word independently
* `0b110000` -- reverse order of 16-bit words

This is implemented by using a series of `log2_width`
`width`-bit wide 2:1 muxes, arranged just like a butterfly network:
https://en.wikipedia.org/wiki/Butterfly_network

To compute `out = grev(inp, 0bxyz)`, where `x`, `y`, and `z` are single bits,
the following permutation network is used:

                inp[0]  inp[1]  inp[2]  inp[3]  inp[4]  inp[5]  inp[6]  inp[7]
                  |       |       |       |       |       |       |       |
the value here is |       |       |       |       |       |       |       |
grev(inp, 0b000): |       |       |       |       |       |       |       |
                  |       |       |       |       |       |       |       |
                  +       +       +       +       +       +       +       +
                  |\     /|       |\     /|       |\     /|       |\     /|
                  | \   / |       | \   / |       | \   / |       | \   / |
                  |  \ /  |       |  \ /  |       |  \ /  |       |  \ /  |
swap 1-bit words: |   X   |       |   X   |       |   X   |       |   X   |
                  |  / \  |       |  / \  |       |  / \  |       |  / \  |
                  | /   \ |       | /   \ |       | /   \ |       | /   \ |
              z--Mux  z--Mux  z--Mux  z--Mux  z--Mux  z--Mux  z--Mux  z--Mux
                  |       |       |       |       |       |       |       |
the value here is |       |       |       |       |       |       |       |
grev(inp, 0b00z): |       |       |       |       |       |       |       |
                  |       |       |       |       |       |       |       |
                  |       | +-----|-------+       |       | +-----|-------+
                  | +-----|-|-----+       |       | +-----|-|-----+       |
                  | |     | |     |       |       | |     | |     |       |
swap 2-bit words: | |     +-|-----|-----+ |       | |     +-|-----|-----+ |
                  +-|-----|-|---+ |     | |       +-|-----|-|---+ |     | |
                  | |     | |   | |     | |       | |     | |   | |     | |
                  | /     | /   \ |     \ |       | /     | /   \ |     \ |
              y--Mux  y--Mux  y--Mux  y--Mux  y--Mux  y--Mux  y--Mux  y--Mux
                  |       |       |       |       |       |       |       |
the value here is |       |       |       |       |       |       |       |
grev(inp, 0b0yz): |       |       |       |       |       |       |       |
                  |       |       |       |       |       |       |       |
                  |       |       |       | +-----|-------|-------|-------+
                  |       |       | +-----|-|-----|-------|-------+       |
                  |       | +-----|-|-----|-|-----|-------+       |       |
                  | +-----|-|-----|-|-----|-|-----+       |       |       |
swap 4-bit words: | |     | |     | |     | |     |       |       |       |
                  | |     | |     | |     +-|-----|-------|-------|-----+ |
                  | |     | |     +-|-----|-|-----|-------|-----+ |     | |
                  | |     +-|-----|-|-----|-|-----|-----+ |     | |     | |
                  +-|-----|-|-----|-|-----|-|---+ |     | |     | |     | |
                  | |     | |     | |     | |   | |     | |     | |     | |
                  | /     | /     | /     | /   \ |     \ |     \ |     \ |
              x--Mux  x--Mux  x--Mux  x--Mux  x--Mux  x--Mux  x--Mux  x--Mux
                  |       |       |       |       |       |       |       |
the value here is |       |       |       |       |       |       |       |
grev(inp, 0bxyz): |       |       |       |       |       |       |       |
                  |       |       |       |       |       |       |       |
                out[0]  out[1]  out[2]  out[3]  out[4]  out[5]  out[6]  out[7]
"""

from nmigen.hdl.ast import Signal, Mux, Cat
from nmigen.hdl.ast import Assert
from nmigen.hdl.dsl import Module
from nmigen.hdl.ir import Elaboratable
from nmigen.back import rtlil
import string


def grev(inval, chunk_sizes, log2_width):
    """Python reference implementation of generalized bit-reverse.
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

    See the module's documentation for a description of generalized
    bit-reverse, as well as the permutation network created by this class.

    Attributes:
    log2_width: int
        see __init__'s docs.
    msb_first: bool
        see __init__'s docs.
    width: int
        the input/output width of the grev operation. The value is
        `2 ** self.log2_width`.
    input: Signal with width=self.width
        the input value of the grev operation.
    chunk_sizes: Signal with width=self.log2_width
        the input that describes which bits get swapped. See the module docs
        for additional details.
    output: Signal with width=self.width
        the output value of the grev operation.
    """

    def __init__(self, log2_width, msb_first=False):
        """Create a `GRev` instance.

        log2_width: int
            the base-2 logarithm of the input/output width of the grev
            operation.
        msb_first: bool
            If `msb_first` is True, then the order will be the reverse of the
            standard order -- swapping adjacent 8-bit words, then 4-bit words,
            then 2-bit words, then 1-bit words -- using the bits of
            `chunk_sizes` from MSB to LSB.
            If `msb_first` is False (the default), then the order will be the
            standard order -- swapping adjacent 1-bit words, then 2-bit words,
            then 4-bit words, then 8-bit words -- using the bits of
            `chunk_sizes` from LSB to MSB.
        """
        self.log2_width = log2_width
        self.msb_first = msb_first
        self.width = 1 << log2_width
        self.input = Signal(self.width)
        self.chunk_sizes = Signal(log2_width)
        self.output = Signal(self.width)

        # internal signals exposed for unit tests, should be ignored by
        # external users. The signals are created in the constructor because
        # that's where all class member variables should *always* be created.
        # If we were to create the members in elaborate() instead, it would
        # just make the class very confusing to use.
        #
        # `_intermediates[step_count]`` is the value after `step_count` steps
        # of muxing. e.g. (for `msb_first == False`) `_intermediates[4]` is the
        # result of 4 steps of muxing, being the value `grev(inp,0b00wxyz)`.
        self._intermediates = [self.__inter(i) for i in range(log2_width + 1)]

    def _get_cs_bit_index(self, step_index):
        """get the index of the bit of `chunk_sizes` that this step should mux
        based off of."""
        assert 0 <= step_index < self.log2_width
        if self.msb_first:
            # reverse so we start from the MSB, producing intermediate values
            # like, for `step_index == 4`, `0buvwx00` rather than `0b00wxyz`
            return self.log2_width - step_index - 1
        return step_index

    def __inter(self, step_count):
        """make a signal with a name like `grev(inp,0b000xyz)` to match the
        diagram in the module-level docs."""
        # make the list of bits in LSB to MSB order
        chunk_sizes_bits = ['0'] * self.log2_width
        # for all steps already completed
        for step_index in range(step_count):
            bit_num = self._get_cs_bit_index(step_index)
            ch = string.ascii_lowercase[-1 - bit_num]  # count from z to a
            chunk_sizes_bits[bit_num] = ch
        # reverse cuz text is MSB first
        chunk_sizes_val = '0b' + ''.join(reversed(chunk_sizes_bits))
        # name works according to Verilog's rules for escaped identifiers cuz
        # it has no spaces
        name = f"grev(inp,{chunk_sizes_val})"
        return Signal(self.width, name=name)

    def __get_permutation(self, step_index):
        """get the bit permutation for the current step. the returned value is
        a list[int] where `retval[i] == j` means that this step's input bit `i`
        goes to this step's output bit `j`."""
        # we can extract just the latest bit for this step, since the previous
        # step effectively has it's value's grev arg as `0b000xyz`, and this
        # step has it's value's grev arg as `0b00wxyz`, so we only need to
        # compute `grev(prev_step_output,0b00w000)` to get
        # `grev(inp,0b00wxyz)`. `cur_chunk_sizes` is the `0b00w000`.
        cur_chunk_sizes = 1 << self._get_cs_bit_index(step_index)
        # compute bit permutation for `grev(...,0b00w000)`.
        return [i ^ cur_chunk_sizes for i in range(self.width)]

    def _sigs_and_expected(self, inp, chunk_sizes):
        """the intermediate signals and the expected values, based off of the
        passed-in `inp` and `chunk_sizes`."""
        # we accumulate a mask of which chunk_sizes bits we have accounted for
        # so far
        chunk_sizes_mask = 0
        for step_count, intermediate in enumerate(self._intermediates):
            # mask out chunk_sizes to get the value
            cur_chunk_sizes = chunk_sizes & chunk_sizes_mask
            expected = grev(inp, cur_chunk_sizes, self.log2_width)
            yield (intermediate, expected)
            # if step_count is in-range for being a valid step_index
            if step_count < self.log2_width:
                # add current step's bit to the mask
                chunk_sizes_mask |= 1 << self._get_cs_bit_index(step_count)
        assert chunk_sizes_mask == 2 ** self.log2_width - 1, \
            "should have got all the bits in chunk_sizes"

    def elaborate(self, platform):
        m = Module()

        # value after zero steps is just the input
        m.d.comb += self._intermediates[0].eq(self.input)

        for step_index in range(self.log2_width):
            step_inp = self._intermediates[step_index]
            step_out = self._intermediates[step_index + 1]
            # get permutation for current step
            permutation = self.__get_permutation(step_index)
            # figure out which `chunk_sizes` bit we want to pay attention to
            # for this step.
            sel = self.chunk_sizes[self._get_cs_bit_index(step_index)]
            for in_index, out_index in enumerate(permutation):
                # use in_index so we get the permuted bit
                permuted_bit = step_inp[in_index]
                # use out_index so we copy the bit straight thru
                straight_bit = step_inp[out_index]
                bit = Mux(sel, permuted_bit, straight_bit)
                m.d.comb += step_out[out_index].eq(bit)
        # value after all steps is just the output
        m.d.comb += self.output.eq(self._intermediates[-1])

        if platform != 'formal':
            return m

        # formal test comparing directly against the (simpler) version
        m.d.comb += Assert(self.output == grev(self.input,
                                               self.chunk_sizes,
                                               self.log2_width))

        for value, expected in self._sigs_and_expected(self.input,
                                                       self.chunk_sizes):
            m.d.comb += Assert(value == expected)
        return m

    def ports(self):
        return [self.input, self.chunk_sizes, self.output]


# useful to see what is going on:
# python3 src/nmutil/test/test_grev.py
# yosys <<<"read_ilang sim_test_out/__main__.TestGrev.test_small/0.il; proc; clean -purge; show top"

if __name__ == '__main__':
    dut = GRev(3)
    vl = rtlil.convert(dut, ports=dut.ports())
    with open("grev3.il", "w") as f:
        f.write(vl)
