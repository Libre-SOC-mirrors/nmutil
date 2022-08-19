# based on microwatt plru.vhdl
# https://github.com/antonblanchard/microwatt/blob/f67b1431655c291fc1c99857a5c1ef624d5b264c/plru.vhdl

# new PLRU API, once all users have migrated to new API in plru2.py, then
# plru2.py will be renamed to plru.py.

from nmigen.hdl.ir import Elaboratable, Display, Signal, Array, Const, Value
from nmigen.hdl.dsl import Module
from nmigen.cli import rtlil
from nmigen.lib.coding import Decoder


class PLRU(Elaboratable):
    r""" PLRU - Pseudo Least Recently Used Replacement

        PLRU-tree indexing:
        lvl0        0
                   / \
                  /   \
                 /     \
        lvl1    1       2
               / \     / \
        lvl2  3   4   5   6
             / \ / \ / \ / \
             ... ... ... ...
    """

    def __init__(self, log2_num_ways, debug=False):
        # type: (int, bool) -> None
        """
        Arguments:
        log2_num_ways: int
            the log-base-2 of the number of cache ways -- BITS in plru.vhdl
        debug: bool
            true if this should print debugging messages at simulation time.
        """
        assert log2_num_ways > 0
        self.log2_num_ways = log2_num_ways
        self.debug = debug
        self.acc_i = Signal(log2_num_ways)
        self.acc_en_i = Signal()
        self.lru_o = Signal(log2_num_ways)

        def mk_tree(i):
            return Signal(name=f"tree_{i}", reset=0)

        # original vhdl has array 1 too big, last entry is never used,
        # subtract 1 to compensate
        self._tree = Array(mk_tree(i) for i in range(self.num_ways - 1))
        """ exposed only for testing """

        def mk_node(i, prefix):
            return Signal(range(self.num_ways), name=f"{prefix}_node_{i}",
                          reset=0)

        nodes_range = range(self.log2_num_ways)

        self._get_lru_nodes = [mk_node(i, "get_lru") for i in nodes_range]
        """ exposed only for testing """

        self._upd_lru_nodes = [mk_node(i, "upd_lru") for i in nodes_range]
        """ exposed only for testing """

    @property
    def num_ways(self):
        return 1 << self.log2_num_ways

    def _display(self, msg, *args):
        if not self.debug:
            return []
        # work around not yet having
        # https://gitlab.com/nmigen/nmigen/-/merge_requests/10
        # by sending through Value.cast()
        return [Display(msg, *map(Value.cast, args))]

    def _get_lru(self, m):
        """ get_lru process in plru.vhdl """
        # XXX Check if we can turn that into a little ROM instead that
        # takes the tree bit vector and returns the LRU. See if it's better
        # in term of FPGA resource usage...
        m.d.comb += self._get_lru_nodes[0].eq(0)
        for i in range(self.log2_num_ways):
            node = self._get_lru_nodes[i]
            val = self._tree[node]
            m.d.comb += self._display("GET: i:%i node:%#x val:%i",
                                      i, node, val)
            m.d.comb += self.lru_o[self.log2_num_ways - 1 - i].eq(val)
            if i != self.log2_num_ways - 1:
                # modified from microwatt version, it uses `node * 2` value
                # to index into tree, rather than using node like is used
                # earlier in this loop iteration
                node <<= 1
                with m.If(val):
                    m.d.comb += self._get_lru_nodes[i + 1].eq(node + 2)
                with m.Else():
                    m.d.comb += self._get_lru_nodes[i + 1].eq(node + 1)

    def _update_lru(self, m):
        """ update_lru process in plru.vhdl """
        with m.If(self.acc_en_i):
            m.d.comb += self._upd_lru_nodes[0].eq(0)
            for i in range(self.log2_num_ways):
                node = self._upd_lru_nodes[i]
                abit = self.acc_i[self.log2_num_ways - 1 - i]
                m.d.sync += [
                    self._tree[node].eq(~abit),
                    self._display("UPD: i:%i node:%#x val:%i",
                                  i, node, ~abit),
                ]
                if i != self.log2_num_ways - 1:
                    node <<= 1
                    with m.If(abit):
                        m.d.comb += self._upd_lru_nodes[i + 1].eq(node + 2)
                    with m.Else():
                        m.d.comb += self._upd_lru_nodes[i + 1].eq(node + 1)

    def elaborate(self, platform=None):
        m = Module()
        self._get_lru(m)
        self._update_lru(m)
        return m

    def __iter__(self):
        yield self.acc_i
        yield self.acc_en_i
        yield self.lru_o

    def ports(self):
        return list(self)


# FIXME: convert PLRUs to new API
# class PLRUs(Elaboratable):
#     def __init__(self, n_plrus, n_bits):
#         self.n_plrus = n_plrus
#         self.n_bits = n_bits
#         self.valid = Signal()
#         self.way = Signal(n_bits)
#         self.index = Signal(n_plrus.bit_length())
#         self.isel = Signal(n_plrus.bit_length())
#         self.o_index = Signal(n_bits)
#
#     def elaborate(self, platform):
#         """Generate TLB PLRUs
#         """
#         m = Module()
#         comb = m.d.comb
#
#         if self.n_plrus == 0:
#             return m
#
#         # Binary-to-Unary one-hot, enabled by valid
#         m.submodules.te = te = Decoder(self.n_plrus)
#         comb += te.n.eq(~self.valid)
#         comb += te.i.eq(self.index)
#
#         out = Array(Signal(self.n_bits, name="plru_out%d" % x)
#                     for x in range(self.n_plrus))
#
#         for i in range(self.n_plrus):
#             # PLRU interface
#             m.submodules["plru_%d" % i] = plru = PLRU(self.n_bits)
#
#             comb += plru.acc_en.eq(te.o[i])
#             comb += plru.acc_i.eq(self.way)
#             comb += out[i].eq(plru.lru_o)
#
#         # select output based on index
#         comb += self.o_index.eq(out[self.isel])
#
#         return m
#
#     def ports(self):
#         return [self.valid, self.way, self.index, self.isel, self.o_index]


if __name__ == '__main__':
    dut = PLRU(3)
    vl = rtlil.convert(dut, ports=dut.ports())
    with open("test_plru.il", "w") as f:
        f.write(vl)

    # dut = PLRUs(4, 2)
    # vl = rtlil.convert(dut, ports=dut.ports())
    # with open("test_plrus.il", "w") as f:
    #     f.write(vl)
