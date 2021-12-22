# SPDX-License-Identifier: LGPL-3-or-later
# TODO: Copyright notice (standard style, plenty of examples)
# Copyright (C) 2021 Luke Kenneth Casson Leighton <lkcl@lkcl.net>
# TODO: credits to NLnet for funding

"""Bitwise logic operators implemented using a look-up table, like LUTs in
FPGAs. Inspired by x86's `vpternlog[dq]` instructions.

https://bugs.libre-soc.org/show_bug.cgi?id=745
https://www.felixcloutier.com/x86/vpternlogd:vpternlogq
"""

from nmigen.hdl.ast import Array, Cat, Repl, Signal
from nmigen.hdl.dsl import Module
from nmigen.hdl.ir import Elaboratable
from nmigen.cli import rtlil


class BitwiseMux(Elaboratable):
    """Mux, but treating input/output Signals as bit vectors, rather than
    integers. This means each bit in the output is independently multiplexed
    based on the corresponding bit in each of the inputs.
    """

    def __init__(self, width):
        self.sel = Signal(width)
        self.t = Signal(width)
        self.f = Signal(width)
        self.output = Signal(width)

    def elaborate(self, platform):
        m = Module()
        m.d.comb += self.output.eq((~self.sel & self.f) | (self.sel & self.t))
        return m


class BitwiseLut(Elaboratable):
    """Bitwise logic operators implemented using a look-up table, like LUTs in
    FPGAs. Inspired by x86's `vpternlog[dq]` instructions.

    Each output bit `i` is set to `lut[Cat(inp[i] for inp in self.inputs)]`
    """

    def __init__(self, input_count, width):
        """
        input_count: int
            the number of inputs. ternlog-style instructions have 3 inputs.
        width: int
            the number of bits in each input/output.
        """
        self.input_count = input_count
        self.width = width

        def inp(i):
            return Signal(width, name=f"input{i}")
        self.inputs = tuple(inp(i) for i in range(input_count))  # inputs
        self.lut = Signal(2 ** input_count)                     # lookup input
        self.output = Signal(width)                             # output

    def elaborate(self, platform):
        m = Module()
        comb = m.d.comb
        lut_array = Array(self.lut)  # create dynamic-indexable LUT array
        out = []

        for bit in range(self.width):
            # take the bit'th bit of every input, create a LUT index from it
            index = Signal(self.input_count, name="index%d" % bit)
            comb += index.eq(Cat(inp[bit] for inp in self.inputs))
            # store output bit in a list - Cat() it after (simplifies graphviz)
            outbit = Signal(name="out%d" % bit)
            comb += outbit.eq(lut_array[index])
            out.append(outbit)

        # finally Cat() all the output bits together
        comb += self.output.eq(Cat(*out))
        return m

    def ports(self):
        return list(self.inputs) + [self.lut, self.output]


class TreeBitwiseLut(Elaboratable):
    """Tree-based version of BitwiseLut. See BitwiseLut for API documentation.
    (good enough reason to say "see bitwiselut", but mention that
    the API is identical and explain why the second implementation
    exists, despite it being identical)
    """

    def __init__(self, input_count, width):
        self.input_count = input_count
        self.width = width

        def inp(i):
            return Signal(width, name=f"input{i}")
        self.inputs = tuple(inp(i) for i in range(input_count))
        self.output = Signal(width)
        self.lut = Signal(2 ** input_count)
        self._mux_inputs = {}
        self._build_mux_inputs()

    def _make_key_str(self, *sel_values):
        k = ['x'] * self.input_count
        for i, v in enumerate(sel_values):
            k[i] = '1' if v else '0'
        return '0b' + ''.join(reversed(k))

    def _build_mux_inputs(self, *sel_values):
        # XXX yyyeah using PHP-style functions-in-text... blech :)
        # XXX replace with name = mux_input_%s" % self._make_etcetc
        name = f"mux_input_{self._make_key_str(*sel_values)}"
        self._mux_inputs[sel_values] = Signal(self.width, name=name)
        if len(sel_values) < self.input_count:
            self._build_mux_inputs(*sel_values, False)
            self._build_mux_inputs(*sel_values, True)

    def elaborate(self, platform):
        m = Module()
        m.d.comb += self.output.eq(self._mux_inputs[()])
        for sel_values, v in self._mux_inputs.items():
            if len(sel_values) < self.input_count:
                # XXX yyyeah using PHP-style functions-in-text... blech :)
                # XXX replace with name = mux_input_%s" % self._make_etcetc
                mux_name = f"mux_{self._make_key_str(*sel_values)}"
                mux = BitwiseMux(self.width)
                setattr(m.submodules, mux_name, mux)
                m.d.comb += [
                    mux.f.eq(self._mux_inputs[(*sel_values, False)]),
                    mux.t.eq(self._mux_inputs[(*sel_values, True)]),
                    mux.sel.eq(self.inputs[len(sel_values)]),
                    v.eq(mux.output),
                ]
            else:
                lut_index = 0
                for i in range(self.input_count):
                    if sel_values[i]:
                        lut_index |= 2 ** i
                m.d.comb += v.eq(Repl(self.lut[lut_index], self.width))
        return m

    def ports(self):
        return [self.input, self.chunk_sizes, self.output]


# useful to see what is going on: use yosys "read_ilang test_lut.il; show top"
if __name__ == '__main__':
    dut = BitwiseLut(3, 8)
    vl = rtlil.convert(dut, ports=dut.ports())
    with open("test_lut.il", "w") as f:
        f.write(vl)
