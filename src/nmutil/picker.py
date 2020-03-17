""" Priority Picker: optimised back-to-back PriorityEncoder and Decoder
    and MultiPriorityPicker: cascading mutually-exclusive pickers

    The input is N bits, the output is N bits wide and only one is
    enabled.
"""

from nmigen import Module, Signal, Cat, Elaboratable, Array, Const
from nmigen.cli import verilog, rtlil

class PriorityPicker(Elaboratable):
    """ implements a priority-picker.  input: N bits, output: N bits
    """
    def __init__(self, wid):
        self.wid = wid
        # inputs
        self.i = Signal(wid, reset_less=True)
        self.o = Signal(wid, reset_less=True)

    def elaborate(self, platform):
        m = Module()

        res = []
        ni = Signal(self.wid, reset_less = True)
        m.d.comb += ni.eq(~self.i)
        for i in range(0, self.wid):
            t = Signal(reset_less = True)
            res.append(t)
            if i == 0:
                m.d.comb += t.eq(self.i[i])
            else:
                m.d.comb += t.eq(~Cat(ni[i], *self.i[:i]).bool())

        # we like Cat(*xxx).  turn lists into concatenated bits
        m.d.comb += self.o.eq(Cat(*res))

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
    """
    def __init__(self, wid, levels):
        self.levels = levels
        self.wid = wid

        self.i = [] # store the array of picker inputs
        self.o = [] # store the array of picker outputs

        for j in range(self.levels):
            i = Signal(self.wid, name="i_%d" % j, reset_less=True)
            o = Signal(self.wid, name="o_%d" % j, reset_less=True)
            self.i.append(i)
            self.o.append(o)
        self.i = Array(self.i)
        self.o = Array(self.o)

    def elaborate(self, platform):
        m = Module()
        comb = m.d.comb

        prev_pp = None
        p_mask = None
        for j in range(self.levels):
            o, i = self.o[j], self.i[j]
            pp = PriorityPicker(self.wid)
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
            prev_pp = pp

        return m

    def __iter__(self):
        yield from self.i
        yield from self.o

    def ports(self):
        return list(self)


if __name__ == '__main__':
    dut = MultiPriorityPicker(5, 4)
    vl = rtlil.convert(dut, ports=dut.ports())
    with open("test_multi_picker.il", "w") as f:
        f.write(vl)
