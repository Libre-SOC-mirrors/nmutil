# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2022 Jacob Lifshay programmerjake@gmail.com

# Funded by NLnet Assure Programme 2021-02-052, https://nlnet.nl/assure part
# of Horizon 2020 EU Programme 957073.

from nmigen import Module
from nmigen.hdl.ast import Value, Const, Signal
from nmutil.plain_data import plain_data
from nmutil.prefix_sum import tree_reduction
from nmigen.cli import rtlil


def pop_count(v, *, width=None, process_temporary=lambda v: v):
    """return the population count (number of 1 bits) of `v`.
    Arguments:
    v: nmigen.Value | int
        the value to calculate the pop-count of.
    width: int | None
        the bit-width of `v`.
        If `width` is None, then `v` must be a nmigen Value or
        match `v`'s width.
    process_temporary: function of (type(v)) -> type(v)
        called after every addition operation, can be used to introduce
        `Signal`s for the intermediate values in the pop-count computation
        like so:

        ```
        def process_temporary(v):
            sig = Signal.like(v)
            m.d.comb += sig.eq(v)
            return sig
        ```
    """
    if isinstance(v, Value):
        if width is None:
            width = len(v)
        assert width == len(v)
        bits = [v[i] for i in range(width)]
        if len(bits) == 0:
            return Const(0)
    else:
        assert width is not None, "width must be given"
        # v and width are ints
        bits = [(v & (1 << i)) != 0 for i in range(width)]
        if len(bits) == 0:
            return 0
    return tree_reduction(bits, fn=lambda a, b: process_temporary(a + b))


# run this as simply "python3 popcount.py" to create an ilang file that
# can be viewed with yosys "read_ilang test_popcount.il; show top"
if __name__ == "__main__":
    m = Module()
    v = Signal(8)
    x = Signal(8)
    pc = pop_count(v, width=8)
    m.d.comb += v.eq(pc)
    vl = rtlil.convert(m)
    with open("test_popcount.il", "w") as f:
        f.write(vl)
