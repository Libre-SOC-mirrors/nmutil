from random import randint
from math import log
from nmigen import Module, Signal, Cat
from nmigen.compat.sim import run_simulation
from nmigen.cli import verilog, rtlil

from nmutil.singlepipe import PassThroughStage
from nmutil.multipipe import (CombMultiInPipeline, PriorityCombMuxInPipe)

from . import StepLimiter
import unittest


class PassData:
    def __init__(self):
        self.muxid = Signal(2, reset_less=True)
        self.idx = Signal(6, reset_less=True)
        self.data = Signal(16, reset_less=True)

    def eq(self, i):
        return [self.muxid.eq(i.muxid), self.idx.eq(i.idx), self.data.eq(i.data)]

    def ports(self):
        return [self.muxid, self.idx, self.data]


def tbench(dut):
    stb = yield dut.out_op.stb
    assert stb == 0
    ack = yield dut.out_op.ack
    assert ack == 0

    # set row 1 input 0
    yield dut.rs[1].in_op[0].eq(5)
    yield dut.rs[1].stb.eq(0b01)  # strobe indicate 1st op ready
    # yield dut.rs[1].ack.eq(1)
    yield

    # check row 1 output (should be inactive)
    decode = yield dut.rs[1].out_decode
    assert decode == 0
    if False:
        op0 = yield dut.rs[1].out_op[0]
        op1 = yield dut.rs[1].out_op[1]
        assert op0 == 0 and op1 == 0

    # output should be inactive
    out_stb = yield dut.out_op.stb
    assert out_stb == 1

    # set row 0 input 1
    yield dut.rs[1].in_op[1].eq(6)
    yield dut.rs[1].stb.eq(0b11)  # strobe indicate both ops ready

    # set acknowledgement of output... takes 1 cycle to respond
    yield dut.out_op.ack.eq(1)
    yield
    yield dut.out_op.ack.eq(0)  # clear ack on output
    yield dut.rs[1].stb.eq(0)  # clear row 1 strobe

    # output strobe should be active, MID should be 0 until "ack" is set...
    out_stb = yield dut.out_op.stb
    assert out_stb == 1
    out_muxid = yield dut.muxid
    assert out_muxid == 0

    # ... and output should not yet be passed through either
    op0 = yield dut.out_op.v[0]
    op1 = yield dut.out_op.v[1]
    assert op0 == 0 and op1 == 0

    # wait for out_op.ack to activate...
    yield dut.rs[1].stb.eq(0b00)  # set row 1 strobes to zero
    yield

    # *now* output should be passed through
    op0 = yield dut.out_op.v[0]
    op1 = yield dut.out_op.v[1]
    assert op0 == 5 and op1 == 6

    # set row 2 input
    yield dut.rs[2].in_op[0].eq(3)
    yield dut.rs[2].in_op[1].eq(4)
    yield dut.rs[2].stb.eq(0b11)  # strobe indicate 1st op ready
    yield dut.out_op.ack.eq(1)  # set output ack
    yield
    yield dut.rs[2].stb.eq(0)  # clear row 2 strobe
    yield dut.out_op.ack.eq(0)  # set output ack
    yield
    op0 = yield dut.out_op.v[0]
    op1 = yield dut.out_op.v[1]
    assert op0 == 3 and op1 == 4, "op0 %d op1 %d" % (op0, op1)
    out_muxid = yield dut.muxid
    assert out_muxid == 2

    # set row 0 and 3 input
    yield dut.rs[0].in_op[0].eq(9)
    yield dut.rs[0].in_op[1].eq(8)
    yield dut.rs[0].stb.eq(0b11)  # strobe indicate 1st op ready
    yield dut.rs[3].in_op[0].eq(1)
    yield dut.rs[3].in_op[1].eq(2)
    yield dut.rs[3].stb.eq(0b11)  # strobe indicate 1st op ready

    # set acknowledgement of output... takes 1 cycle to respond
    yield dut.out_op.ack.eq(1)
    yield
    yield dut.rs[0].stb.eq(0)  # clear row 1 strobe
    yield
    out_muxid = yield dut.muxid
    assert out_muxid == 0, "out muxid %d" % out_muxid

    yield
    yield dut.rs[3].stb.eq(0)  # clear row 1 strobe
    yield dut.out_op.ack.eq(0)  # clear ack on output
    yield
    out_muxid = yield dut.muxid
    assert out_muxid == 3, "out muxid %d" % out_muxid


class InputTest:
    def __init__(self, dut):
        self.dut = dut
        self.di = {}
        self.do = {}
        self.tlen = 10
        for muxid in range(dut.num_rows):
            self.di[muxid] = {}
            self.do[muxid] = {}
            for i in range(self.tlen):
                self.di[muxid][i] = randint(0, 100) + (muxid << 8)
                self.do[muxid][i] = self.di[muxid][i]

    def send(self, muxid):
        for i in range(self.tlen):
            op2 = self.di[muxid][i]
            rs = self.dut.p[muxid]
            yield rs.i_valid.eq(1)
            yield rs.i_data.data.eq(op2)
            yield rs.i_data.idx.eq(i)
            yield rs.i_data.muxid.eq(muxid)
            yield
            o_p_ready = yield rs.o_ready
            step_limiter = StepLimiter(10000)
            while not o_p_ready:
                step_limiter.step()
                yield
                o_p_ready = yield rs.o_ready

            print("send", muxid, i, hex(op2))

            yield rs.i_valid.eq(0)
            # wait random period of time before queueing another value
            for i in range(randint(0, 3)):
                yield

        yield rs.i_valid.eq(0)
        # wait random period of time before queueing another value
        # for i in range(randint(0, 3)):
        #    yield

        #send_range = randint(0, 3)
        # if send_range == 0:
        #    send = True
        # else:
        #    send = randint(0, send_range) != 0

    def rcv(self):
        for _ in StepLimiter(10000):
            #stall_range = randint(0, 3)
            # for j in range(randint(1,10)):
            #    stall = randint(0, stall_range) != 0
            #    yield self.dut.n[0].i_ready.eq(stall)
            #    yield
            n = self.dut.n
            yield n.i_ready.eq(1)
            yield
            o_n_valid = yield n.o_valid
            i_n_ready = yield n.i_ready
            if not o_n_valid or not i_n_ready:
                continue

            muxid = yield n.o_data.muxid
            out_i = yield n.o_data.idx
            out_v = yield n.o_data.data

            print("recv", muxid, out_i, hex(out_v))

            # see if this output has occurred already, delete it if it has
            assert out_i in self.do[muxid], "out_i %d not in array %s" % \
                (out_i, repr(self.do[muxid]))
            assert self.do[muxid][out_i] == out_v  # pass-through data
            del self.do[muxid][out_i]

            # check if there's any more outputs
            zerolen = True
            for (k, v) in self.do.items():
                if v:
                    zerolen = False
            if zerolen:
                break


class TestPriorityMuxPipe(PriorityCombMuxInPipe):
    def __init__(self):
        self.num_rows = 4
        def iospecfn(): return PassData()
        stage = PassThroughStage(iospecfn)
        PriorityCombMuxInPipe.__init__(self, stage, p_len=self.num_rows)


@unittest.skip("disabled for now: logic loop")  # FIXME
def test1():
    dut = TestPriorityMuxPipe()
    vl = rtlil.convert(dut, ports=dut.ports())
    with open("test_inputgroup_multi.il", "w") as f:
        f.write(vl)
    #run_simulation(dut, tbench(dut), vcd_name="test_inputgroup.vcd")

    test = InputTest(dut)
    run_simulation(dut, [test.send(1), test.send(0),
                         test.send(3), test.send(2),
                         test.rcv()],
                   vcd_name="test_inputgroup_multi.vcd")


if __name__ == '__main__':
    test1()
