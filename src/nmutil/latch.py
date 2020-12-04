"""
    This work is funded through NLnet under Grant 2019-02-012

    License: LGPLv3+


"""
from nmigen.compat.sim import run_simulation
from nmigen.cli import verilog, rtlil
from nmigen import Record, Signal, Module, Const, Elaboratable, Mux

""" jk latch

module jk(q,q1,j,k,c);
output q,q1;
input j,k,c;
reg q,q1;
initial begin q=1'b0; q1=1'b1; end
always @ (posedge c)
  begin
    case({j,k})
         {1'b0,1'b0}:begin q=q; q1=q1; end
         {1'b0,1'b1}: begin q=1'b0; q1=1'b1; end
         {1'b1,1'b0}:begin q=1'b1; q1=1'b0; end
         {1'b1,1'b1}: begin q=~q; q1=~q1; end
    endcase
   end
endmodule
"""


def latchregister(m, incoming, outgoing, settrue, name=None):
    """latchregister

    based on a conditon, "settrue", incoming data will be "latched"
    into a register and passed out on "outgoing".

    * if "settrue" is ASSERTED, outgoing is COMBINATORIALLY equal to incoming
    * on the same cycle that settrue is DEASSERTED, outgoing REMAINS
      equal (indefinitely) to the incoming value
    """
    # make reg same as input. reset OK.
    if isinstance(incoming, Record):
        reg = Record.like(incoming, name=name)
    else:
        reg = Signal.like(incoming, name=name)
    m.d.comb += outgoing.eq(Mux(settrue, incoming, reg))
    with m.If(settrue): # pass in some kind of expression/condition here
        m.d.sync += reg.eq(incoming)      # latch input into register


def mkname(prefix, suffix):
    if suffix is None:
        return prefix
    return "%s_%s" % (prefix, suffix)


class SRLatch(Elaboratable):
    def __init__(self, sync=True, llen=1, name=None):
        self.sync = sync
        self.llen = llen
        s_n, r_n = mkname("s", name), mkname("r", name)
        q_n, qn_n = mkname("q", name), mkname("qn", name)
        qlq_n = mkname("qlq", name)
        self.s = Signal(llen, name=s_n, reset=0)
        self.r = Signal(llen, name=r_n, reset=(1<<llen)-1) # defaults to off
        self.q = Signal(llen, name=q_n, reset_less=True)
        self.qn = Signal(llen, name=qn_n, reset_less=True)
        self.qlq = Signal(llen, name=qlq_n, reset_less=True)

    def elaborate(self, platform):
        m = Module()
        q_int = Signal(self.llen)

        m.d.sync += q_int.eq((q_int & ~self.r) | self.s)
        if self.sync:
            m.d.comb += self.q.eq(q_int)
        else:
            m.d.comb += self.q.eq((q_int & ~self.r) | self.s)
        m.d.comb += self.qn.eq(~self.q)
        m.d.comb += self.qlq.eq(self.q | q_int) # useful output

        return m

    def ports(self):
        return self.s, self.r, self.q, self.qn


def sr_sim(dut):
    yield dut.s.eq(0)
    yield dut.r.eq(0)
    yield
    yield
    yield
    yield dut.s.eq(1)
    yield
    yield
    yield
    yield dut.s.eq(0)
    yield
    yield
    yield
    yield dut.r.eq(1)
    yield
    yield
    yield
    yield dut.r.eq(0)
    yield
    yield
    yield

def test_sr():
    dut = SRLatch(llen=4)
    vl = rtlil.convert(dut, ports=dut.ports())
    with open("test_srlatch.il", "w") as f:
        f.write(vl)

    run_simulation(dut, sr_sim(dut), vcd_name='test_srlatch.vcd')

    dut = SRLatch(sync=False, llen=4)
    vl = rtlil.convert(dut, ports=dut.ports())
    with open("test_srlatch_async.il", "w") as f:
        f.write(vl)

    run_simulation(dut, sr_sim(dut), vcd_name='test_srlatch_async.vcd')

if __name__ == '__main__':
    test_sr()
