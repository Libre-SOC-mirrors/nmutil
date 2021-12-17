# SPDX-License-Identifier: LGPL-3-or-later
"""
Bitwise logic operators implemented using a look-up table, like LUTs in
FPGAs. Inspired by x86's `vpternlog[dq]` instructions.

https://bugs.libre-soc.org/show_bug.cgi?id=745
https://www.felixcloutier.com/x86/vpternlogd:vpternlogq
"""

from nmigen.hdl.ast import Array, Cat, Repl, Signal
from nmigen.hdl.dsl import Module
from nmigen.hdl.ir import Elaboratable


class BitwiseMux(Elaboratable):
    """ Mux, but treating input/output Signals as bit vectors, rather than
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
    """ Bitwise logic operators implemented using a look-up table, like LUTs in
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
        self.inputs = tuple(inp(i) for i in range(input_count))
        """ the inputs """
        self.output = Signal(width)
        """ the output """
        self.lut = Signal(2 ** input_count)
        """ the look-up table. Is `2 ** input_count` bits wide."""

    def elaborate(self, platform):
        m = Module()
        lut_array = Array(self.lut)
        for bit in range(self.width):
            index = Cat(inp[bit] for inp in self.inputs)
            m.d.comb += self.output[bit].eq(lut_array[index])
        return m


class TreeBitwiseLut(Elaboratable):
    """ Tree-based version of BitwiseLut. See BitwiseLut for API documentation.
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
