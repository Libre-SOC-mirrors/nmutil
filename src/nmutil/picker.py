""" Priority Picker: optimised back-to-back PriorityEncoder and Decoder
    and MultiPriorityPicker: cascading mutually-exclusive pickers

    PriorityPicker: the input is N bits, the output is N bits wide and
    only one is enabled.

    MultiPriorityPicker: likewise except that there are M pickers and
    each output is guaranteed mutually exclusive.  Optionally:
    an "index" (and enable line) is also outputted.

    MultiPriorityPicker is designed for port-selection, when there are
    multiple "things" (of width N) contending for access to M "ports".
    When the M=0 "thing" requests a port, it gets allocated port 0
    (always).  However if the M=0 "thing" does *not* request a port,
    this gives the M=1 "thing" the opportunity to gain access to port 0.

    Given that N may potentially be much greater than M (16 bits wide
    where M may be e.g. only 4) we can't just ok, "ok so M=N therefore
    M=0 gets access to port 0, M=1 gets access to port 1" etc.
"""

from nmigen import Module, Signal, Cat, Elaboratable, Array, Const, Mux
from nmigen.cli import verilog, rtlil
import math


class PriorityPicker(Elaboratable):
    """ implements a priority-picker.  input: N bits, output: N bits
    """
    def __init__(self, wid):
        self.wid = wid
        # inputs
        self.i = Signal(wid, reset_less=True)
        self.o = Signal(wid, reset_less=True)
        self.en_o = Signal(reset_less=True) # true if any output is true

    def elaborate(self, platform):
        m = Module()

        # works by saying, "if all previous bits were zero, we get a chance"
        res = []
        ni = Signal(self.wid, reset_less = True)
        m.d.comb += ni.eq(~self.i)
        for i in range(0, self.wid):
            t = Signal(name="t%d" % i, reset_less = True)
            res.append(t)
            if i == 0:
                m.d.comb += t.eq(self.i[i])
            else:
                m.d.comb += t.eq(~Cat(ni[i], *self.i[:i]).bool())

        # we like Cat(*xxx).  turn lists into concatenated bits
        m.d.comb += self.o.eq(Cat(*res))
        # useful "is any output enabled" signal
        m.d.comb += self.en_o.eq(self.o.bool()) # true if 1 input is true

        return m

    def __iter__(self):
        yield self.i
        yield self.o

    def ports(self):
        return list(self)


class MultiPriorityPicker(Elaboratable):
    """ implements a multi-input priority picker
        Mx inputs of N bits, Mx outputs of N bits, only one is set

        Each picker masks out the one below it, such that the first
        gets top priority, the second cannot have the same bit that
        the first has set, and so on.  To do this, a "mask" accumulates
        the output from the chain, masking the input to the next chain.

        Also outputted (optional): an index for each picked "thing".
    """
    def __init__(self, wid, levels, indices=False):
        self.levels = levels
        self.wid = wid
        self.indices = indices

        # only the one input, but multiple (single) bit outputs
        self.i = Signal(self.wid, reset_less=True)

        # create array of (single-bit) outputs (unary)
        o_l = [] # array of picker outputs
        for j in range(self.levels):
            o = Signal(self.wid, name="o_%d" % j, reset_less=True)
            o_l.append(o)
        self.o = Array(o_l)

        # add an array of "enables"
        self.en_o = Signal(self.levels, name="en_o", reset_less=True)

        if not self.indices:
            return

        # add an array of indices
        lidx = math.ceil(math.log2(self.levels))
        idx_o = [] # store the array of indices
        for j in range(self.levels):
            i = Signal(lidx, name="idxo_%d" % j, reset_less=True)
            idx_o.append(i)
        self.idx_o = Array(idx_o)

    def elaborate(self, platform):
        m = Module()
        comb = m.d.comb

        # create Priority Pickers, accumulate their outputs and prevent
        # the next one in the chain from selecting that output bit.
        # the input from the current picker will be "masked" and connected
        # to the *next* picker on the next loop
        prev_pp = None
        p_mask = None
        pp_l = []
        i = self.i
        for j in range(self.levels):
            o = self.o[j]
            pp = PriorityPicker(self.wid)
            pp_l.append(pp)
            setattr(m.submodules, "pp%d" % j, pp)
            comb += o.eq(pp.o)
            if prev_pp is None:
                comb += pp.i.eq(i)
                p_mask = Const(0, self.wid)
            else:
                mask = Signal(self.wid, name="m_%d" % j, reset_less=True)
                comb += mask.eq(prev_pp.o | p_mask) # accumulate output bits
                comb += pp.i.eq(i & ~mask)          # mask out input
                p_mask = mask
            i = pp.i # for input to next round
            prev_pp = pp

        # accumulate the enables
        en_l = []
        for j in range(self.levels):
            en_l.append(pp_l[j].en_o)
        # concat accumulated enable bits
        comb += self.en_o.eq(Cat(*en_l))

        if not self.indices:
            return m

        # for each picker enabled, pass that out and set a cascading index
        lidx = math.ceil(math.log2(self.levels))
        prev_count = None
        for j in range(self.levels):
            en_o = pp_l[j].en_o
            if prev_count is None:
                comb += self.idx_o[j].eq(0)
            else:
                count1 = Signal(lidx, name="count_%d" % j, reset_less=True)
                comb += count1.eq(prev_count + Const(1, lidx))
                comb += self.idx_o[j].eq(Mux(en_o, count1, prev_count))
            prev_count = self.idx_o[j]

        return m

    def __iter__(self):
        yield self.i
        yield from self.o
        if not self.indices:
            return
        yield self.en_o
        yield from self.idx_o

    def ports(self):
        return list(self)


if __name__ == '__main__':
    dut = PriorityPicker(16)
    vl = rtlil.convert(dut, ports=dut.ports())
    with open("test_picker.il", "w") as f:
        f.write(vl)
    dut = MultiPriorityPicker(5, 4, True)
    vl = rtlil.convert(dut, ports=dut.ports())
    with open("test_multi_picker.il", "w") as f:
        f.write(vl)
    dut = MultiPriorityPicker(5, 4, False)
    vl = rtlil.convert(dut, ports=dut.ports())
    with open("test_multi_picker_noidx.il", "w") as f:
        f.write(vl)
