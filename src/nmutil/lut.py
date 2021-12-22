# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2021 Jacob Lifshay
# Copyright (C) 2021 Luke Kenneth Casson Leighton <lkcl@lkcl.net>

# Funded by NLnet Assure Programme 2021-02-052, https://nlnet.nl/assure part
# of Horizon 2020 EU Programme 957073.

"""Bitwise logic operators implemented using a look-up table, like LUTs in
FPGAs. Inspired by x86's `vpternlog[dq]` instructions.

https://bugs.libre-soc.org/show_bug.cgi?id=745
https://www.felixcloutier.com/x86/vpternlogd:vpternlogq
"""

from nmigen.hdl.ast import Array, Cat, Repl, Signal
from nmigen.hdl.dsl import Module
from nmigen.hdl.ir import Elaboratable
from nmigen.cli import rtlil
from dataclasses import dataclass


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


@dataclass
class _TreeMuxNode:
    """Mux in tree for `TreeBitwiseLut`."""
    out: Signal
    container: "TreeBitwiseLut"
    parent: "_TreeMuxNode | None"
    child0: "_TreeMuxNode | None"
    child1: "_TreeMuxNode | None"
    depth: int

    @property
    def child_index(self):
        """index of this node, when looked up in this node's parent's children.
        """
        if self.parent is None:
            return None
        return int(self.parent.child1 is self)

    def add_child(self, child_index):
        node = _TreeMuxNode(
            out=Signal(self.container.width),
            container=self.container, parent=self,
            child0=None, child1=None, depth=1 + self.depth)
        if child_index:
            assert self.child1 is None
            self.child1 = node
        else:
            assert self.child0 is None
            self.child0 = node
        node.out.name = "node_out_" + node.key_str
        return node

    @property
    def key(self):
        retval = []
        node = self
        while node.parent is not None:
            retval.append(node.child_index)
            node = node.parent
        retval.reverse()
        return retval

    @property
    def key_str(self):
        k = ['x'] * self.container.input_count
        for i, v in enumerate(self.key):
            k[i] = '1' if v else '0'
        return '0b' + ''.join(reversed(k))


class TreeBitwiseLut(Elaboratable):
    """Tree-based version of BitwiseLut. Has identical API, so see `BitwiseLut`
    for API documentation. This version may produce more efficient hardware.
    """

    def __init__(self, input_count, width):
        self.input_count = input_count
        self.width = width

        def inp(i):
            return Signal(width, name=f"input{i}")
        self.inputs = tuple(inp(i) for i in range(input_count))
        self.output = Signal(width)
        self.lut = Signal(2 ** input_count)
        self._tree_root = _TreeMuxNode(
            out=self.output, container=self, parent=None,
            child0=None, child1=None, depth=0)
        self._build_tree(self._tree_root)

    def _build_tree(self, node):
        if node.depth < self.input_count:
            self._build_tree(node.add_child(0))
            self._build_tree(node.add_child(1))

    def _elaborate_tree(self, m, node):
        if node.depth < self.input_count:
            mux = BitwiseMux(self.width)
            setattr(m.submodules, "mux_" + node.key_str, mux)
            m.d.comb += [
                mux.f.eq(node.child0.out),
                mux.t.eq(node.child1.out),
                mux.sel.eq(self.inputs[node.depth]),
                node.out.eq(mux.output),
            ]
            self._elaborate_tree(m, node.child0)
            self._elaborate_tree(m, node.child1)
        else:
            index = int(node.key_str, base=2)
            m.d.comb += node.out.eq(Repl(self.lut[index], self.width))

    def elaborate(self, platform):
        m = Module()
        self._elaborate_tree(m, self._tree_root)
        return m

    def ports(self):
        return [*self.inputs, self.lut, self.output]


# useful to see what is going on:
# yosys <<<"read_ilang sim_test_out/__main__.TestBitwiseLut.test_tree/0.il; proc;;; show top"
