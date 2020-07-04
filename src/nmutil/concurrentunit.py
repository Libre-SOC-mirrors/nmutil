""" concurrent unit from mitch alsup augmentations to 6600 scoreboard

    * data fans in
    * data goes through a pipeline
    * results fan back out.

    the output data format has to have a member "muxid", which is used
    as the array index on fan-out
"""

from math import log
from nmigen import Module, Elaboratable
from nmigen.cli import main, verilog

from nmutil.singlepipe import PassThroughStage
from nmutil.multipipe import CombMuxOutPipe
from nmutil.multipipe import PriorityCombMuxInPipe


def num_bits(n):
    return int(log(n) / log(2))


class InMuxPipe(PriorityCombMuxInPipe):
    def __init__(self, num_rows, iospecfn, maskwid=0):
        self.num_rows = num_rows
        stage = PassThroughStage(iospecfn)
        PriorityCombMuxInPipe.__init__(self, stage, p_len=self.num_rows,
                                       maskwid=maskwid)


class MuxOutPipe(CombMuxOutPipe):
    def __init__(self, num_rows, iospecfn, maskwid=0):
        self.num_rows = num_rows
        stage = PassThroughStage(iospecfn)
        CombMuxOutPipe.__init__(self, stage, n_len=self.num_rows,
                                maskwid=maskwid)


class ReservationStations(Elaboratable):
    """ Reservation-Station pipeline

        Input: num_rows - number of input and output Reservation Stations

        Requires: the addition of an "alu" object, from which ispec and ospec
        are taken, and inpipe and outpipe are connected to it

        * fan-in on inputs (an array of BaseData: a,b,mid)
        * ALU pipeline
        * fan-out on outputs (an array of FPPackData: z,mid)

        Fan-in and Fan-out are combinatorial.
    """
    def __init__(self, num_rows, maskwid=0, feedback_width=None):
        self.num_rows = nr = num_rows
        self.feedback_width = feedback_width
        self.inpipe = InMuxPipe(nr, self.i_specfn, maskwid)   # fan-in
        self.outpipe = MuxOutPipe(nr, self.o_specfn, maskwid) # fan-out

        self.p = self.inpipe.p  # kinda annoying,
        self.n = self.outpipe.n # use pipe in/out as this class in/out
        self._ports = self.inpipe.ports() + self.outpipe.ports()

    def elaborate(self, platform):
        m = Module()
        m.submodules.inpipe = self.inpipe
        m.submodules.alu = self.alu
        m.submodules.outpipe = self.outpipe

        m.d.comb += self.inpipe.n.connect_to_next(self.alu.p)
        m.d.comb += self.alu.connect_to_next(self.outpipe)

        if self.feedback_width is None:
            return m

        # connect all outputs above the feedback width back to their inputs
        # (hence, feedback).  pipeline stages are then expected to *modify*
        # the muxid (with care) in order to use the "upper numbered" RSes
        # for storing partially-completed results.  micro-coding, basically

        for i in range(self.feedback_width, self.num_rows):
            self.outpipe.n[i].connect_to_next(self.inpipe.p[i])

        return m

    def ports(self):
        return self._ports

    def i_specfn(self):
        return self.alu.ispec()

    def o_specfn(self):
        return self.alu.ospec()
