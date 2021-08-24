""" key strategic example showing how to do multi-input fan-in into a
    multi-stage pipeline, then multi-output fanout, with an unary muxid
    and cancellation

    the multiplex ID from the fan-in is passed in to the pipeline, preserved,
    and used as a routing ID on the fanout.
"""

from random import randint
from math import log
from nmigen import Module, Signal, Cat, Value, Elaboratable, Const
from nmigen.compat.sim import run_simulation
from nmigen.cli import verilog, rtlil

from nmutil.multipipe import CombMultiOutPipeline, CombMuxOutPipe
from nmutil.multipipe import PriorityCombMuxInPipe
from nmutil.singlepipe import MaskCancellable, RecordObject, Object

from nmutil.test import StepLimiter
import unittest


class PassData(Object):
    def __init__(self):
        Object.__init__(self)
        self.muxid = Signal(2, reset_less=True)
        self.idx = Signal(8, reset_less=True)
        self.data = Signal(16, reset_less=True)
        self.operator = Signal(2, reset_less=True)
        self.routeid = Signal(2, reset_less=True)  # muxidname


class PassThroughStage:
    def __init__(self):
        self.o = self.ospec()

    def ispec(self):
        return PassData()

    def ospec(self):
        return self.ispec()  # same as ospec

    def _setup(self, m, i):
        comb = m.d.comb
        #comb += self.o.eq(i)

    def process(self, i):
        return i


class SplitRouteStage:
    def __init__(self):
        self.o = self.ospec()

    def ispec(self):
        return PassData()

    def ospec(self):
        return PassData()

    def setup(self, m, i):
        comb = m.d.comb
        comb += self.o.eq(i)
        with m.If(i.operator == Const(1, 2)):
            # selects 2nd output in CombMuxOutPipe
            comb += self.o.routeid.eq(1)
            comb += self.o.data.eq(i.data + 1)  # add 1 to say "we did it"
            comb += self.o.operator.eq(2)  # don't get into infinite loop
        with m.Else():
            # selects 2nd output in CombMuxOutPipe
            comb += self.o.routeid.eq(0)

    def process(self, i):
        return self.o


class DecisionPipe(MaskCancellable):
    def __init__(self, maskwid):
        stage = SplitRouteStage()
        MaskCancellable.__init__(self, stage, maskwid)


class RouteBackPipe(CombMuxOutPipe):
    """ routes data back to start of pipeline
    """

    def __init__(self):
        stage = PassThroughStage()
        CombMuxOutPipe.__init__(self, stage, n_len=2,
                                maskwid=4, muxidname="routeid",
                                routemask=True)


class MergeRoutePipe(PriorityCombMuxInPipe):
    """ merges data coming from end of pipe (with operator now == 1)
    """

    def __init__(self):
        stage = PassThroughStage()
        PriorityCombMuxInPipe.__init__(self, stage, p_len=2, maskwid=4,
                                       routemask=True)


class PassThroughPipe(MaskCancellable):
    def __init__(self, maskwid):
        MaskCancellable.__init__(self, PassThroughStage(), maskwid)


class InputTest:
    def __init__(self, dut, tlen):
        self.dut = dut
        self.di = {}
        self.do = {}
        self.sent = {}
        self.tlen = tlen
        for muxid in range(dut.num_rows):
            self.di[muxid] = {}
            self.do[muxid] = {}
            self.sent[muxid] = []
            for i in range(self.tlen):
                self.di[muxid][i] = randint(0, 255) + (muxid << 8)
                self.do[muxid][i] = self.di[muxid][i]

    def send(self, muxid):
        for i in range(self.tlen):
            op2 = self.di[muxid][i]
            rs = self.dut.p[muxid]
            yield rs.i_valid.eq(1)
            yield rs.data_i.data.eq(op2)
            yield rs.data_i.idx.eq(i)
            yield rs.data_i.muxid.eq(muxid)
            yield rs.data_i.operator.eq(1)
            yield rs.mask_i.eq(1)
            yield
            o_p_ready = yield rs.o_ready
            step_limiter = StepLimiter(10000)
            while not o_p_ready:
                step_limiter.step()
                yield
                o_p_ready = yield rs.o_ready

            print("send", muxid, i, hex(op2), op2)
            self.sent[muxid].append(i)

            yield rs.i_valid.eq(0)
            yield rs.mask_i.eq(0)
            # wait until it's received
            step_limiter = StepLimiter(10000)
            while i in self.do[muxid]:
                step_limiter.step()
                yield

            # wait random period of time before queueing another value
            for i in range(randint(0, 3)):
                yield

        yield rs.i_valid.eq(0)
        yield

        print("send ended", muxid)

        # wait random period of time before queueing another value
        # for i in range(randint(0, 3)):
        #    yield

        #send_range = randint(0, 3)
        # if send_range == 0:
        #    send = True
        # else:
        #    send = randint(0, send_range) != 0

    def rcv(self, muxid):
        rs = self.dut.p[muxid]
        for _ in StepLimiter(10000):

            # check cancellation
            if False and self.sent[muxid] and randint(0, 2) == 0:
                todel = self.sent[muxid].pop()
                print("to delete", muxid, self.sent[muxid], todel)
                if todel in self.do[muxid]:
                    del self.do[muxid][todel]
                    yield rs.stop_i.eq(1)
                print("left", muxid, self.do[muxid])
                if len(self.do[muxid]) == 0:
                    break

            #stall_range = randint(0, 3)
            # for j in range(randint(1,10)):
            #    stall = randint(0, stall_range) != 0
            #    yield self.dut.n[0].i_ready.eq(stall)
            #    yield

            n = self.dut.n[muxid]
            yield n.i_ready.eq(1)
            yield
            yield rs.stop_i.eq(0)  # resets cancel mask
            o_n_valid = yield n.o_valid
            i_n_ready = yield n.i_ready
            if not o_n_valid or not i_n_ready:
                continue

            out_muxid = yield n.data_o.muxid
            out_i = yield n.data_o.idx
            out_v = yield n.data_o.data

            print("recv", out_muxid, out_i, hex(out_v), hex(out_v))

            # see if this output has occurred already, delete it if it has
            assert muxid == out_muxid, \
                "out_muxid %d not correct %d" % (out_muxid, muxid)
            if out_i not in self.sent[muxid]:
                print("cancelled/recv", muxid, out_i)
                continue
            assert out_i in self.do[muxid], "out_i %d not in array %s" % \
                (out_i, repr(self.do[muxid]))
            assert self.do[muxid][out_i] + 1 == out_v  # check data
            del self.do[muxid][out_i]
            todel = self.sent[muxid].index(out_i)
            del self.sent[muxid][todel]

            # check if there's any more outputs
            if len(self.do[muxid]) == 0:
                break

        print("recv ended", muxid)


class TestPriorityMuxPipe(PriorityCombMuxInPipe):
    def __init__(self, num_rows):
        self.num_rows = num_rows
        stage = PassThroughStage()
        PriorityCombMuxInPipe.__init__(self, stage,
                                       p_len=self.num_rows, maskwid=1)


class TestMuxOutPipe(CombMuxOutPipe):
    def __init__(self, num_rows):
        self.num_rows = num_rows
        stage = PassThroughStage()
        CombMuxOutPipe.__init__(self, stage, n_len=self.num_rows,
                                maskwid=1)


class TestInOutPipe(Elaboratable):
    def __init__(self, num_rows=4):
        self.num_rows = nr = num_rows
        self.inpipe = TestPriorityMuxPipe(nr)  # fan-in (combinatorial)
        self.mergein = MergeRoutePipe()       # merge in feedback
        self.pipe1 = PassThroughPipe(nr)      # stage 1 (clock-sync)
        self.pipe2 = DecisionPipe(nr)         # stage 2 (clock-sync)
        # self.pipe3 = PassThroughPipe(nr)      # stage 3 (clock-sync)
        # self.pipe4 = PassThroughPipe(nr)      # stage 4 (clock-sync)
        self.splitback = RouteBackPipe()      # split back to mergein
        self.outpipe = TestMuxOutPipe(nr)     # fan-out (combinatorial)
        self.fifoback = PassThroughPipe(nr)   # temp route-back store

        self.p = self.inpipe.p  # kinda annoying,
        self.n = self.outpipe.n  # use pipe in/out as this class in/out
        self._ports = self.inpipe.ports() + self.outpipe.ports()

    def elaborate(self, platform):
        m = Module()
        m.submodules.inpipe = self.inpipe
        m.submodules.mergein = self.mergein
        m.submodules.pipe1 = self.pipe1
        m.submodules.pipe2 = self.pipe2
        #m.submodules.pipe3 = self.pipe3
        #m.submodules.pipe4 = self.pipe4
        m.submodules.splitback = self.splitback
        m.submodules.outpipe = self.outpipe
        m.submodules.fifoback = self.fifoback

        m.d.comb += self.inpipe.n.connect_to_next(self.mergein.p[0])
        m.d.comb += self.mergein.n.connect_to_next(self.pipe1.p)
        m.d.comb += self.pipe1.connect_to_next(self.pipe2)
        #m.d.comb += self.pipe2.connect_to_next(self.pipe3)
        #m.d.comb += self.pipe3.connect_to_next(self.pipe4)
        m.d.comb += self.pipe2.connect_to_next(self.splitback)
        m.d.comb += self.splitback.n[1].connect_to_next(self.fifoback.p)
        m.d.comb += self.fifoback.n.connect_to_next(self.mergein.p[1])
        m.d.comb += self.splitback.n[0].connect_to_next(self.outpipe.p)

        return m

    def ports(self):
        return self._ports


@unittest.skip("buggy -- fails due to exceeding step count limit")  # FIXME
def test1():
    dut = TestInOutPipe()
    vl = rtlil.convert(dut, ports=dut.ports())
    with open("test_inoutmux_feedback_pipe.il", "w") as f:
        f.write(vl)

    tlen = 5

    test = InputTest(dut, tlen)
    run_simulation(dut, [test.rcv(0),  # test.rcv(1),
                         #test.rcv(3), test.rcv(2),
                         test.send(0),  # test.send(1),
                         #test.send(3), test.send(2),
                         ],
                   vcd_name="test_inoutmux_feedback_pipe.vcd")


if __name__ == '__main__':
    #from cProfile import Profile
    #p = Profile()
    # p.enable()
    test1()
    # p.disable()
    # p.print_stats()
