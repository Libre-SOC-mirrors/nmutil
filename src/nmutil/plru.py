# based on ariane plru, from tlb.sv

from nmigen import Signal, Module, Cat, Const, Repl, Array
from nmigen.hdl.ir import Elaboratable
from nmigen.cli import rtlil
from nmigen.utils import log2_int
from nmigen.lib.coding import Decoder


class PLRU(Elaboratable):
    r""" PLRU - Pseudo Least Recently Used Replacement

        PLRU-tree indexing:
        lvl0        0
                   / \
                  /   \
        lvl1     1     2
                / \   / \
        lvl2   3   4 5   6
              / \ /\/\  /\
             ... ... ... ...
    """

    def __init__(self, BITS):
        self.BITS = BITS
        self.acc_i = Signal(BITS)
        self.acc_en = Signal()
        self.lru_o = Signal(BITS)

    def elaborate(self, platform=None):
        m = Module()

        # Tree (bit per entry)
        TLBSZ = 2*(self.BITS-1)
        plru_tree = Signal(TLBSZ)

        # Just predefine which nodes will be set/cleared
        # E.g. for a TLB with 8 entries, the for-loop is semantically
        # equivalent to the following pseudo-code:
        # unique case (1'b1)
        # acc_en[7]: plru_tree[0, 2, 6] = {1, 1, 1};
        # acc_en[6]: plru_tree[0, 2, 6] = {1, 1, 0};
        # acc_en[5]: plru_tree[0, 2, 5] = {1, 0, 1};
        # acc_en[4]: plru_tree[0, 2, 5] = {1, 0, 0};
        # acc_en[3]: plru_tree[0, 1, 4] = {0, 1, 1};
        # acc_en[2]: plru_tree[0, 1, 4] = {0, 1, 0};
        # acc_en[1]: plru_tree[0, 1, 3] = {0, 0, 1};
        # acc_en[0]: plru_tree[0, 1, 3] = {0, 0, 0};
        # default: begin /* No hit */ end
        # endcase

        LOG_TLB = log2_int(self.BITS, False)
        hit = Signal(self.BITS, reset_less=True)
        m.d.comb += hit.eq(Repl(self.acc_en, self.BITS) & self.acc_i)

        for i in range(self.BITS):
            # we got a hit so update the pointer as it was least recently used
            with m.If(hit[i]):
                # Set the nodes to the values we would expect
                for lvl in range(LOG_TLB):
                    idx_base = (1 << lvl)-1
                    # lvl0 <=> MSB, lvl1 <=> MSB-1, ...
                    shift = LOG_TLB - lvl
                    new_idx = Const(~((i >> (shift-1)) & 1), 1)
                    plru_idx = idx_base + (i >> shift)
                    # print("plru", i, lvl, hex(idx_base),
                    #      plru_idx, shift, new_idx)
                    m.d.sync += plru_tree[plru_idx].eq(new_idx)

        # Decode tree to write enable signals
        # Next for-loop basically creates the following logic for e.g.
        # an 8 entry TLB (note: pseudo-code obviously):
        # replace_en[7] = &plru_tree[ 6, 2, 0]; #plru_tree[0,2,6]=={1,1,1}
        # replace_en[6] = &plru_tree[~6, 2, 0]; #plru_tree[0,2,6]=={1,1,0}
        # replace_en[5] = &plru_tree[ 5,~2, 0]; #plru_tree[0,2,5]=={1,0,1}
        # replace_en[4] = &plru_tree[~5,~2, 0]; #plru_tree[0,2,5]=={1,0,0}
        # replace_en[3] = &plru_tree[ 4, 1,~0]; #plru_tree[0,1,4]=={0,1,1}
        # replace_en[2] = &plru_tree[~4, 1,~0]; #plru_tree[0,1,4]=={0,1,0}
        # replace_en[1] = &plru_tree[ 3,~1,~0]; #plru_tree[0,1,3]=={0,0,1}
        # replace_en[0] = &plru_tree[~3,~1,~0]; #plru_tree[0,1,3]=={0,0,0}
        # For each entry traverse the tree. If every tree-node matches
        # the corresponding bit of the entry's index, this is
        # the next entry to replace.
        replace = []
        for i in range(self.BITS):
            en = []
            for lvl in range(LOG_TLB):
                idx_base = (1 << lvl)-1
                # lvl0 <=> MSB, lvl1 <=> MSB-1, ...
                shift = LOG_TLB - lvl
                new_idx = (i >> (shift-1)) & 1
                plru_idx = idx_base + (i >> shift)
                plru = Signal(reset_less=True,
                              name="plru-%d-%d-%d-%d" %
                              (i, lvl, plru_idx, new_idx))
                m.d.comb += plru.eq(plru_tree[plru_idx])
                if new_idx:
                    en.append(~plru)  # yes inverted (using bool() below)
                else:
                    en.append(plru)  # yes inverted (using bool() below)
            #print("plru", i, en)
            # boolean logic manipulation:
            # plru0 & plru1 & plru2 == ~(~plru0 | ~plru1 | ~plru2)
            replace.append(~Cat(*en).bool())
        m.d.comb += self.lru_o.eq(Cat(*replace))

        return m

    def ports(self):
        return [self.acc_en, self.lru_o, self.acc_i]


class PLRUs(Elaboratable):
    def __init__(self, n_plrus, n_bits):
        self.n_plrus = n_plrus
        self.n_bits = n_bits
        self.valid = Signal()
        self.way = Signal(n_bits)
        self.index = Signal(n_plrus.bit_length())
        self.isel = Signal(n_plrus.bit_length())
        self.o_index = Signal(n_bits)

    def elaborate(self, platform):
        """Generate TLB PLRUs
        """
        m = Module()
        comb = m.d.comb

        if self.n_plrus == 0:
            return m

        # Binary-to-Unary one-hot, enabled by valid
        m.submodules.te = te = Decoder(self.n_plrus)
        comb += te.n.eq(~self.valid)
        comb += te.i.eq(self.index)

        out = Array(Signal(self.n_bits, name="plru_out%d" % x)
                    for x in range(self.n_plrus))

        for i in range(self.n_plrus):
            # PLRU interface
            m.submodules["plru_%d" % i] = plru = PLRU(self.n_bits)

            comb += plru.acc_en.eq(te.o[i])
            comb += plru.acc_i.eq(self.way)
            comb += out[i].eq(plru.lru_o)

        # select output based on index
        comb += self.o_index.eq(out[self.isel])

        return m

    def ports(self):
        return [self.valid, self.way, self.index, self.isel, self.o_index]


if __name__ == '__main__':
    dut = PLRU(3)
    vl = rtlil.convert(dut, ports=dut.ports())
    with open("test_plru.il", "w") as f:
        f.write(vl)

    dut = PLRUs(4, 2)
    vl = rtlil.convert(dut, ports=dut.ports())
    with open("test_plrus.il", "w") as f:
        f.write(vl)
