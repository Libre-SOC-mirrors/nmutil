"""
    This work is funded through NLnet under Grant 2019-02-012

    License: LGPLv3+


"""

from nmigen import Module, Signal, Elaboratable
from nmigen.utils import log2_int

def masked(m_out, m_in, mask):
    return (m_out & ~mask) | (m_in & mask)


class Mask(Elaboratable):
    def __init__(self, sz):
        self.sz = sz
        self.shift = Signal(log2_int(sz, False)+1)
        self.mask = Signal(sz)

    def elaborate(self, platform):
        m = Module()

        for i in range(self.sz):
            with m.If(self.shift > i):
                m.d.comb += self.mask[i].eq(1)

        return m

