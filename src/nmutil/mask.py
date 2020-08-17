from nmigen import Module, Signal, Elaboratable
from nmigen.utils import log2_int


class Mask(Elaboratable):
    def __init__(self, sz):
        self.sz = sz
        self.shift = Signal(log2_int(sz, False))
        self.mask = Signal(sz)

    def elaborate(self, platform):
        m = Module()

        for i in range(self.sz):
            with m.If(self.shift > i):
                m.d.comb += self.mask[i].eq(1)

        return m

