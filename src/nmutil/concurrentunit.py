# SPDX-License-Identifier: LGPL-3-or-later
""" concurrent unit from mitch alsup augmentations to 6600 scoreboard

    This work is funded through NLnet under Grant 2019-02-012

    License: LGPLv3+


    * data fans in
    * data goes through a pipeline
    * results fan back out.

    the output data format has to have a member "muxid", which is used
    as the array index on fan-out

    Associated bugreports:

    * https://bugs.libre-soc.org/show_bug.cgi?id=538
"""

from math import log
from nmigen import Module, Elaboratable, Signal, Cat
from nmigen.asserts import Assert
from nmigen.lib.coding import PriorityEncoder
from nmigen.cli import main, verilog

from nmutil.singlepipe import PassThroughStage
from nmutil.multipipe import CombMuxOutPipe
from nmutil.multipipe import PriorityCombMuxInPipe
from nmutil.iocontrol import NextControl, PrevControl
from nmutil import nmoperator


def num_bits(n):
    return int(log(n) / log(2))


class PipeContext:

    def __init__(self, pspec):
        """ creates a pipeline context.  currently: operator (op) and muxid

            opkls (within pspec) - the class to create that will be the
                                   "operator". instance must have an "eq"
                                   function.
        """
        self.id_wid = pspec.id_wid
        self.op_wid = pspec.op_wid
        self.muxid = Signal(self.id_wid, reset_less=True)   # RS multiplex ID
        opkls = pspec.opkls
        if opkls is None:
            self.op = Signal(self.op_wid, reset_less=True)
        else:
            self.op = opkls(pspec)

    def eq(self, i):
        ret = [self.muxid.eq(i.muxid)]
        ret.append(self.op.eq(i.op))
        # don't forget to update matches if you add fields later.
        return ret

    def matches(self, another):
        """
        Returns a list of Assert()s validating that this context
        matches the other context.
        """
        # I couldn't figure a clean way of overloading the == operator.
        return [
            Assert(self.muxid == another.muxid),
            Assert(self.op == another.op),
        ]

    def __iter__(self):
        yield self.muxid
        yield self.op

    def ports(self):
        if hasattr(self.op, "ports"):
            return [self.muxid] + self.op.ports()
        else:
            return list(self)


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


class ALUProxy:
    """ALUProxy: create a series of ALUs that look like the ALU being
    sandwiched in between the fan-in and fan-out.  One ALU looks like
    it is multiple concurrent ALUs
    """

    def __init__(self, alu, p, n):
        self.alu = alu
        self.p = p
        self.n = n


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
        self.outpipe = MuxOutPipe(nr, self.o_specfn, maskwid)  # fan-out

        self.p = self.inpipe.p  # kinda annoying,
        self.n = self.outpipe.n  # use pipe in/out as this class in/out
        self._ports = self.inpipe.ports() + self.outpipe.ports()

    def setup_pseudoalus(self):
        """setup_pseudoalus: establishes a suite of pseudo-alus
        that look to all pipeline-intents-and-purposes just like the original
        """
        self.pseudoalus = []
        for i in range(self.num_rows):
            self.pseudoalus.append(ALUProxy(self.alu, self.p[i], self.n[i]))

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


class ReservationStations2(Elaboratable):
    """ Reservation-Station pipeline.  Manages an ALU and makes it look like
        there are multiple of them, presenting the same ready/valid API

        Input:

        :alu: - an ALU to be "managed" by these ReservationStations
        :num_rows: - number of input and output Reservation Stations

        Note that the ALU data (in and out specs) right the way down the
        entire chain *must* have a "muxid" data member.  this is picked
        up and used to route data correctly from input RS to output RS.

        It is the responsibility of the USER of the ReservationStations
        class to correctly set that muxid in each data packet to the
        correct constant.  this could change in future.

        FAILING TO SET THE MUXID IS GUARANTEED TO RESULT IN CORRUPTED DATA.
    """

    def __init__(self, alu, num_rows, alu_name=None):
        if alu_name is None:
            alu_name = "alu"
        self.num_rows = nr = num_rows
        id_wid = num_rows.bit_length()
        self.p = []
        self.n = []
        self.alu = alu
        self.alu_name = alu_name
        # create prev and next ready/valid and add replica of ALU data specs
        for i in range(num_rows):
            suffix = "_%d" % i
            p = PrevControl(name=suffix)
            n = NextControl(name=suffix)
            p.i_data, n.o_data = self.alu.new_specs("rs_%d" % i)
            self.p.append(p)
            self.n.append(n)

        self.pipe = self  # for Arbiter to select the incoming prevcontrols

        # set up pseudo-alus that look like a standard pipeline
        self.pseudoalus = []
        for i in range(self.num_rows):
            self.pseudoalus.append(ALUProxy(self.alu, self.p[i], self.n[i]))

    def __iter__(self):
        for p in self.p:
            yield from p
        for n in self.n:
            yield from n

    def ports(self):
        return list(self)

    def elaborate(self, platform):
        m = Module()
        pe = PriorityEncoder(self.num_rows)  # input priority picker
        m.submodules[self.alu_name] = self.alu
        m.submodules.selector = pe
        for i, (p, n) in enumerate(zip(self.p, self.n)):
            m.submodules["rs_p_%d" % i] = p
            m.submodules["rs_n_%d" % i] = n

        # Priority picker for one RS
        self.active = Signal()
        self.m_id = Signal.like(pe.o)

        # ReservationStation status information, progressively updated in FSM
        rsvd = Signal(self.num_rows)  # indicates RS data in flight
        sent = Signal(self.num_rows)  # sent indicates data in pipeline
        wait = Signal(self.num_rows)  # the outputs are waiting for accept

        # pick first non-reserved ReservationStation with data not already
        # sent into the ALU
        m.d.comb += pe.i.eq(rsvd & ~sent)
        m.d.comb += self.active.eq(~pe.n)   # encoder active (one input valid)
        m.d.comb += self.m_id.eq(pe.o)       # output one active input

        # mux in and mux out ids.  note that all data *must* have a muxid
        mid = self.m_id                   # input mux selector
        o_muxid = self.alu.n.o_data.muxid  # output mux selector

        # technically speaking this could be set permanently "HI".
        # when all the ReservationStations outputs are waiting,
        # the ALU cannot obviously accept any more data.  as the
        # ALU is effectively "decoupled" from (managed by) the RSes,
        # as long as there is sufficient RS allocation this should not
        # be necessary, i.e. at no time should the ALU be given more inputs
        # than there are outputs to accept (!) but just in case...
        m.d.comb += self.alu.n.i_ready.eq(~wait.all())

        #####
        # input side
        #####

        # first, establish input: select one input to pass data to (p_mux)
        for i in range(self.num_rows):
            i_buf, o_buf = self.alu.new_specs("buf%d" % i)  # buffers
            with m.FSM():
                # indicate ready to accept data, and accept it if incoming
                # BUT, if there is an opportunity to send on immediately
                # to the ALU, take it early (combinatorial)
                with m.State("ACCEPTING%d" % i):
                    m.d.comb += self.p[i].o_ready.eq(1)  # ready indicator
                    with m.If(self.p[i].i_valid):  # valid data incoming
                        m.d.sync += rsvd[i].eq(1)  # now reserved
                        # a unique opportunity: the ALU happens to be free
                        with m.If(mid == i):  # picker selected us
                            with m.If(self.alu.p.o_ready):  # ALU can accept
                                # transfer
                                m.d.comb += self.alu.p.i_valid.eq(1)
                                m.d.comb += nmoperator.eq(self.alu.p.i_data,
                                                          self.p[i].i_data)
                                m.d.sync += sent[i].eq(1)  # now reserved
                                m.next = "WAITOUT%d" % i  # move to "wait output"
                        with m.Else():
                            # nope. ALU wasn't free. try next cycle(s)
                            m.d.sync += nmoperator.eq(i_buf, self.p[i].i_data)
                            m.next = "ACCEPTED%d" % i  # move to "accepted"

                # now try to deliver to the ALU, but only if we are "picked"
                with m.State("ACCEPTED%d" % i):
                    with m.If(mid == i):  # picker selected us
                        with m.If(self.alu.p.o_ready):  # ALU can accept
                            m.d.comb += self.alu.p.i_valid.eq(1)  # transfer
                            m.d.comb += nmoperator.eq(self.alu.p.i_data, i_buf)
                            m.d.sync += sent[i].eq(1)  # now reserved
                            m.next = "WAITOUT%d" % i  # move to "wait output"

                # waiting for output to appear on the ALU, take a copy
                # BUT, again, if there is an opportunity to send on
                # immediately, take it (combinatorial)
                with m.State("WAITOUT%d" % i):
                    with m.If(o_muxid == i):  # when ALU output matches our RS
                        with m.If(self.alu.n.o_valid):  # ALU can accept
                            # second unique opportunity: the RS is ready
                            with m.If(self.n[i].i_ready):  # ready to receive
                                m.d.comb += self.n[i].o_valid.eq(1)  # valid
                                m.d.comb += nmoperator.eq(self.n[i].o_data,
                                                          self.alu.n.o_data)
                                m.d.sync += wait[i].eq(0)  # clear waiting
                                m.d.sync += sent[i].eq(0)  # and sending
                                m.d.sync += rsvd[i].eq(0)  # and reserved
                                m.next = "ACCEPTING%d" % i  # back to "accepting"
                            with m.Else():
                                # nope. RS wasn't ready. try next cycles
                                m.d.sync += wait[i].eq(1)  # now waiting
                                m.d.sync += nmoperator.eq(o_buf,
                                                          self.alu.n.o_data)
                                m.next = "SENDON%d" % i  # move to "send data on"

                # waiting for "valid" indicator on RS output: deliver it
                with m.State("SENDON%d" % i):
                    with m.If(self.n[i].i_ready):  # user is ready to receive
                        m.d.comb += self.n[i].o_valid.eq(1)  # indicate valid
                        m.d.comb += nmoperator.eq(self.n[i].o_data, o_buf)
                        m.d.sync += wait[i].eq(0)  # clear waiting
                        m.d.sync += sent[i].eq(0)  # and sending
                        m.d.sync += rsvd[i].eq(0)  # and reserved
                        m.next = "ACCEPTING%d" % i  # and back to "accepting"

        return m
