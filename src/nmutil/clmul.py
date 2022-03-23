# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2021 Jacob Lifshay programmerjake@gmail.com

# Funded by NLnet Assure Programme 2021-02-052, https://nlnet.nl/assure part
# of Horizon 2020 EU Programme 957073.

""" Carry-less Multiplication.

https://bugs.libre-soc.org/show_bug.cgi?id=784
"""

from functools import reduce
from operator import xor
from nmigen.hdl.ir import Elaboratable
from nmigen.hdl.ast import Signal, Cat, Repl, Value
from nmigen.hdl.dsl import Module


class BitwiseXorReduce(Elaboratable):
    """Bitwise Xor lots of stuff together by using tree-reduction on each bit.

    Properties:
    input_values: tuple[Value, ...]
        input nmigen Values
    output: Signal
        output, set to `input_values[0] ^ input_values[1] ^ input_values[2]...`
    """

    def __init__(self, input_values):
        self.input_values = tuple(map(Value.cast, input_values))
        assert len(self.input_values) > 0, "can't xor-reduce nothing"
        self.output = Signal(reduce(xor, self.input_values).shape())

    def elaborate(self, platform):
        m = Module()
        # collect inputs into full-width Signals
        inputs = []
        for i, inp_v in enumerate(self.input_values):
            inp = self.output.like(self.output, name=f"input_{i}")
            # sign/zero-extend inp_v to full-width
            m.d.comb += inp.eq(inp_v)
            inputs.append(inp)
        for bit in range(self.output.width):
            # construct a tree-reduction for bit index `bit` of all inputs
            m.d.comb += self.output[bit].eq(Cat(i[bit] for i in inputs).xor())
        return m


class CLMulAdd(Elaboratable):
    """Carry-less multiply-add.

        Computes:
        ```
        self.output = (clmul(self.factor1, self.factor2) ^ self.terms[0]
            ^ self.terms[1] ^ self.terms[2] ...)
        ```

        Properties:
        factor_width: int
            the bit-width of `factor1` and `factor2`
        term_widths: tuple[int, ...]
            the bit-width of each Signal in `terms`
        factor1: Signal of width self.factor_width
            the first input to the carry-less multiplication section
        factor2: Signal of width self.factor_width
            the second input to the carry-less multiplication section
        terms: tuple[Signal, ...]
            inputs to be carry-less added (really XOR)
        output: Signal
            the final output
    """

    def __init__(self, factor_width, term_widths=()):
        assert isinstance(factor_width, int) and factor_width >= 1
        self.factor_width = factor_width
        self.term_widths = tuple(map(int, term_widths))

        # build Signals
        self.factor1 = Signal(self.factor_width)
        self.factor2 = Signal(self.factor_width)

        def terms():
            for i, inp in enumerate(self.term_widths):
                yield Signal(inp, name=f"term_{i}")
        self.terms = tuple(terms())
        self.output = Signal(max((self.factor_width * 2 - 1,
                                  *self.term_widths)))

    def __reduce_inputs(self):
        for shift in range(self.factor_width):
            mask = Repl(self.factor2[shift], self.factor_width)
            yield (self.factor1 & mask) << shift
        yield from self.terms

    def elaborate(self, platform):
        m = Module()
        xor_reduce = BitwiseXorReduce(self.__reduce_inputs())
        m.submodules.xor_reduce = xor_reduce
        m.d.comb += self.output.eq(xor_reduce.output)
        return m
