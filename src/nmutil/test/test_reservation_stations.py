""" key strategic example showing how to do multi-input fan-in into a
    multi-stage pipeline, then multi-output fanout.

    the multiplex ID from the fan-in is passed in to the pipeline, preserved,
    and used as a routing ID on the fanout.
"""

from random import randint
from math import log
from nmigen import Module, Signal, Cat, Value, Elaboratable
from nmigen.compat.sim import run_simulation
from nmigen.cli import verilog, rtlil

from nmutil.concurrentunit import ReservationStations2
from nmutil.singlepipe import SimpleHandshake, RecordObject, Object


class PassData2(RecordObject):
    def __init__(self):
        RecordObject.__init__(self)
        self.muxid = Signal(2, reset_less=True)
        self.idx = Signal(8, reset_less=True)
        self.data = Signal(16, reset_less=True)


class PassData(Object):
    def __init__(self, name=None):
        Object.__init__(self)
        if name is None:
            name = ""
        self.muxid = Signal(2, name="muxid"+name, reset_less=True)
        self.idx = Signal(8, name="idx"+name, reset_less=True)
        self.data = Signal(16, name="data"+name, reset_less=True)


class PassThroughStage:
    def ispec(self, name=None):
        return PassData(name=name)

    def ospec(self, name=None):
        return self.ispec(name)  # same as ospec

    def process(self, i):
        return i  # pass-through


class PassThroughPipe(SimpleHandshake):
    def __init__(self):
        SimpleHandshake.__init__(self, PassThroughStage())


class InputTest:
    def __init__(self, dut):
        self.dut = dut
        self.di = {}
        self.do = {}
        self.tlen = 100
        for muxid in range(dut.num_rows):
            self.di[muxid] = {}
            self.do[muxid] = {}
            for i in range(self.tlen):
                self.di[muxid][i] = randint(0, 255) + (muxid << 8)
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
            while not o_p_ready:
                yield
                o_p_ready = yield rs.o_ready

            print("send", muxid, i, hex(op2))

            yield rs.i_valid.eq(0)
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
        while True:
            #stall_range = randint(0, 3)
            # for j in range(randint(1,10)):
            #    stall = randint(0, stall_range) != 0
            #    yield self.dut.n[0].i_ready.eq(stall)
            #    yield
            n = self.dut.n[muxid]
            yield n.i_ready.eq(1)
            yield
            o_n_valid = yield n.o_valid
            i_n_ready = yield n.i_ready
            if not o_n_valid or not i_n_ready:
                continue

            out_muxid = yield n.o_data.muxid
            out_i = yield n.o_data.idx
            out_v = yield n.o_data.data

            print("recv", out_muxid, out_i, hex(out_v))

            # see if this output has occurred already, delete it if it has
            assert muxid == out_muxid, \
                "out_muxid %d not correct %d" % (out_muxid, muxid)
            assert out_i in self.do[muxid], "out_i %d not in array %s" % \
                (out_i, repr(self.do[muxid]))
            assert self.do[muxid][out_i] == out_v  # pass-through data
            del self.do[muxid][out_i]

            # check if there's any more outputs
            if len(self.do[muxid]) == 0:
                break
        print("recv ended", muxid)


class TestALU(Elaboratable):
    def __init__(self):
        self.pipe1 = PassThroughPipe()              # stage 1 (clock-sync)
        self.pipe2 = PassThroughPipe()              # stage 2 (clock-sync)

        self.p = self.pipe1.p
        self.n = self.pipe2.n
        self._ports = self.pipe1.ports() + self.pipe2.ports()

    def elaborate(self, platform):
        m = Module()
        m.submodules.pipe1 = self.pipe1
        m.submodules.pipe2 = self.pipe2

        m.d.comb += self.pipe1.connect_to_next(self.pipe2)

        return m

    def new_specs(self, name):
        return self.pipe1.ispec(name), self.pipe2.ospec(name)

    def ports(self):
        return self._ports


def test1():
    alu = TestALU()
    dut = ReservationStations2(alu, num_rows=4)
    vl = rtlil.convert(dut, ports=dut.ports())
    with open("test_reservation_stations.il", "w") as f:
        f.write(vl)
    #run_simulation(dut, testbench(dut), vcd_name="test_inputgroup.vcd")

    test = InputTest(dut)
    run_simulation(dut, [test.rcv(1), test.rcv(0),
                         test.rcv(3), test.rcv(2),
                         test.send(0), test.send(1),
                         test.send(3), test.send(2),
                         ],
                   vcd_name="test_reservation_stations.vcd")


if __name__ == '__main__':
    test1()
