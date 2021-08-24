""" IO Control API

    This work is funded through NLnet under Grant 2019-02-012

    License: LGPLv3+


    Associated development bugs:
    * http://bugs.libre-riscv.org/show_bug.cgi?id=538
    * http://bugs.libre-riscv.org/show_bug.cgi?id=148
    * http://bugs.libre-riscv.org/show_bug.cgi?id=64
    * http://bugs.libre-riscv.org/show_bug.cgi?id=57

    Important: see Stage API (stageapi.py) in combination with below

    Main classes: PrevControl and NextControl.

    These classes manage the data and the synchronisation state
    to the previous and next stage, respectively.  ready/valid
    signals are used by the Pipeline classes to tell if data
    may be safely passed from stage to stage.

    The connection from one stage to the next is carried out with
    NextControl.connect_to_next.  It is *not* necessary to have
    a PrevControl.connect_to_prev because it is functionally
    directly equivalent to prev->next->connect_to_next.
"""

from nmigen import Signal, Cat, Const, Module, Value, Elaboratable
from nmigen.cli import verilog, rtlil
from nmigen.hdl.rec import Record
from nmigen import tracer

from collections.abc import Sequence, Iterable
from collections import OrderedDict

from nmutil import nmoperator


class Object:
    def __init__(self):
        self.fields = OrderedDict()

    def __setattr__(self, k, v):
        print ("kv", k, v)
        if (k.startswith('_') or k in ["fields", "name", "src_loc"] or
           k in dir(Object) or "fields" not in self.__dict__):
            return object.__setattr__(self, k, v)
        self.fields[k] = v

    def __getattr__(self, k):
        if k in self.__dict__:
            return object.__getattr__(self, k)
        try:
            return self.fields[k]
        except KeyError as e:
            raise AttributeError(e)

    def __iter__(self):
        for x in self.fields.values():  # OrderedDict so order is preserved
            if isinstance(x, Iterable):
                yield from x
            else:
                yield x

    def eq(self, inp):
        res = []
        for (k, o) in self.fields.items():
            i = getattr(inp, k)
            print ("eq", o, i)
            rres = o.eq(i)
            if isinstance(rres, Sequence):
                res += rres
            else:
                res.append(rres)
        print (res)
        return res

    def ports(self): # being called "keys" would be much better
        return list(self)


def add_prefix_to_record_signals(prefix, record):
    """recursively hunt through Records, modifying names to add a prefix
    """
    for key, val in record.fields.items():
        if isinstance(val, Signal):
            val.name = prefix + val.name
        elif isinstance(val, Record):
            add_prefix_to_record_signals(prefix, val)


class RecordObject(Record):
    def __init__(self, layout=None, name=None):
        #if name is None:
        #    name = tracer.get_var_name(depth=2, default="$ro")
        Record.__init__(self, layout=layout or [], name=name)


    def __setattr__(self, k, v):
        #print(f"RecordObject setattr({k}, {v})")
        #print (dir(Record))
        if (k.startswith('_') or k in ["fields", "name", "src_loc"] or
           k in dir(Record) or "fields" not in self.__dict__):
            return object.__setattr__(self, k, v)

        if self.name is None:
            prefix = ""
        else:
            prefix = self.name + "_"
        # Prefix the signal name with the name of the recordobject
        if isinstance(v, Signal):
            #print (self, self.name, v.name)
            v.name = prefix + v.name
        elif isinstance(v, Record):
            add_prefix_to_record_signals(prefix, v)

        self.fields[k] = v
        #print ("RecordObject setattr", k, v)
        if isinstance(v, Record):
            newlayout = {k: (k, v.layout)}
        elif isinstance(v, Value):
            newlayout = {k: (k, v.shape())}
        else:
            newlayout = {k: (k, nmoperator.shape(v))}
        self.layout.fields.update(newlayout)

    def __iter__(self):
        for x in self.fields.values(): # remember: fields is an OrderedDict
            if hasattr(x, 'ports'):
                yield from x.ports()
            elif isinstance(x, Record):
                for f in x.fields.values():
                    yield f
            elif isinstance(x, Iterable):
                yield from x           # a bit like flatten (nmigen.tools)
            else:
                yield x

    def ports(self): # would be better being called "keys"
        return list(self)


class PrevControl(Elaboratable):
    """ contains signals that come *from* the previous stage (both in and out)
        * i_valid: previous stage indicating all incoming data is valid.
                   may be a multi-bit signal, where all bits are required
                   to be asserted to indicate "valid".
        * o_ready: output to next stage indicating readiness to accept data
        * i_data : an input - MUST be added by the USER of this class
    """

    def __init__(self, i_width=1, stage_ctl=False, maskwid=0, offs=0):
        self.stage_ctl = stage_ctl
        self.maskwid = maskwid
        if maskwid:
            self.mask_i = Signal(maskwid)                # prev   >>in  self
            self.stop_i = Signal(maskwid)                # prev   >>in  self
        self.i_valid = Signal(i_width, name="p_i_valid") # prev   >>in  self
        self._o_ready = Signal(name="p_o_ready")         # prev   <<out self
        self.i_data = None # XXX MUST BE ADDED BY USER
        if stage_ctl:
            self.s_o_ready = Signal(name="p_s_o_rdy")    # prev   <<out self
        self.trigger = Signal(reset_less=True)

    @property
    def o_ready(self):
        """ public-facing API: indicates (externally) that stage is ready
        """
        if self.stage_ctl:
            return self.s_o_ready # set dynamically by stage
        return self._o_ready      # return this when not under dynamic control

    def _connect_in(self, prev, direct=False, fn=None,
                    do_data=True, do_stop=True):
        """ internal helper function to connect stage to an input source.
            do not use to connect stage-to-stage!
        """
        i_valid = prev.i_valid if direct else prev.i_valid_test
        res = [self.i_valid.eq(i_valid),
               prev.o_ready.eq(self.o_ready)]
        if self.maskwid:
            res.append(self.mask_i.eq(prev.mask_i))
            if do_stop:
                res.append(self.stop_i.eq(prev.stop_i))
        if do_data is False:
            return res
        i_data = fn(prev.i_data) if fn is not None else prev.i_data
        return res + [nmoperator.eq(self.i_data, i_data)]

    @property
    def i_valid_test(self):
        vlen = len(self.i_valid)
        if vlen > 1:
            # multi-bit case: valid only when i_valid is all 1s
            all1s = Const(-1, (len(self.i_valid), False))
            i_valid = (self.i_valid == all1s)
        else:
            # single-bit i_valid case
            i_valid = self.i_valid

        # when stage indicates not ready, incoming data
        # must "appear" to be not ready too
        if self.stage_ctl:
            i_valid = i_valid & self.s_o_ready

        return i_valid

    def elaborate(self, platform):
        m = Module()
        m.d.comb += self.trigger.eq(self.i_valid_test & self.o_ready)
        return m

    def eq(self, i):
        res = [nmoperator.eq(self.i_data, i.i_data),
                self.o_ready.eq(i.o_ready),
                self.i_valid.eq(i.i_valid)]
        if self.maskwid:
            res.append(self.mask_i.eq(i.mask_i))
        return res

    def __iter__(self):
        yield self.i_valid
        yield self.o_ready
        if self.maskwid:
            yield self.mask_i
            yield self.stop_i
        if hasattr(self.i_data, "ports"):
            yield from self.i_data.ports()
        elif (isinstance(self.i_data, Sequence) or
              isinstance(self.i_data, Iterable)):
            yield from self.i_data
        else:
            yield self.i_data

    def ports(self):
        return list(self)


class NextControl(Elaboratable):
    """ contains the signals that go *to* the next stage (both in and out)
        * o_valid: output indicating to next stage that data is valid
        * i_ready: input from next stage indicating that it can accept data
        * o_data : an output - MUST be added by the USER of this class
    """
    def __init__(self, stage_ctl=False, maskwid=0):
        self.stage_ctl = stage_ctl
        self.maskwid = maskwid
        if maskwid:
            self.mask_o = Signal(maskwid)       # self out>>  next
            self.stop_o = Signal(maskwid)       # self out>>  next
        self.o_valid = Signal(name="n_o_valid") # self out>>  next
        self.i_ready = Signal(name="n_i_ready") # self <<in   next
        self.o_data = None # XXX MUST BE ADDED BY USER
        #if self.stage_ctl:
        self.d_valid = Signal(reset=1) # INTERNAL (data valid)
        self.trigger = Signal(reset_less=True)

    @property
    def i_ready_test(self):
        if self.stage_ctl:
            return self.i_ready & self.d_valid
        return self.i_ready

    def connect_to_next(self, nxt, do_data=True, do_stop=True):
        """ helper function to connect to the next stage data/valid/ready.
            data/valid is passed *TO* nxt, and ready comes *IN* from nxt.
            use this when connecting stage-to-stage

            note: a "connect_from_prev" is completely unnecessary: it's
            just nxt.connect_to_next(self)
        """
        res = [nxt.i_valid.eq(self.o_valid),
               self.i_ready.eq(nxt.o_ready)]
        if self.maskwid:
            res.append(nxt.mask_i.eq(self.mask_o))
            if do_stop:
                res.append(nxt.stop_i.eq(self.stop_o))
        if do_data:
            res.append(nmoperator.eq(nxt.i_data, self.o_data))
        print ("connect to next", self, self.maskwid, nxt.i_data,
                                  do_data, do_stop)
        return res

    def _connect_out(self, nxt, direct=False, fn=None,
                     do_data=True, do_stop=True):
        """ internal helper function to connect stage to an output source.
            do not use to connect stage-to-stage!
        """
        i_ready = nxt.i_ready if direct else nxt.i_ready_test
        res = [nxt.o_valid.eq(self.o_valid),
               self.i_ready.eq(i_ready)]
        if self.maskwid:
            res.append(nxt.mask_o.eq(self.mask_o))
            if do_stop:
                res.append(nxt.stop_o.eq(self.stop_o))
        if not do_data:
            return res
        o_data = fn(nxt.o_data) if fn is not None else nxt.o_data
        return res + [nmoperator.eq(o_data, self.o_data)]

    def elaborate(self, platform):
        m = Module()
        m.d.comb += self.trigger.eq(self.i_ready_test & self.o_valid)
        return m

    def __iter__(self):
        yield self.i_ready
        yield self.o_valid
        if self.maskwid:
            yield self.mask_o
            yield self.stop_o
        if hasattr(self.o_data, "ports"):
            yield from self.o_data.ports()
        elif (isinstance(self.o_data, Sequence) or
              isinstance(self.o_data, Iterable)):
            yield from self.o_data
        else:
            yield self.o_data

    def ports(self):
        return list(self)

