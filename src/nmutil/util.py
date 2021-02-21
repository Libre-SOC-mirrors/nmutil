"""
    This work is funded through NLnet under Grant 2019-02-012

    License: LGPLv3+

"""

from collections.abc import Iterable
from nmigen import Mux, Signal, Cat

# XXX this already exists in nmigen._utils
# see https://bugs.libre-soc.org/show_bug.cgi?id=297
def flatten(v):
    if isinstance(v, Iterable):
        for i in v:
            yield from flatten(i)
    else:
        yield v

# tree reduction function.  operates recursively.
def treereduce(tree, op, fn):
    """treereduce: apply a map-reduce to a list.
    examples: OR-reduction of one member of a list of Records down to a
              single data point:
              treereduce(tree, operator.or_, lambda x: getattr(x, "data_o"))
    """
    #print ("treereduce", tree)
    if not isinstance(tree, list):
        return tree
    if len(tree) == 1:
        return fn(tree[0])
    if len(tree) == 2:
        return op(fn(tree[0]), fn(tree[1]))
    s = len(tree) // 2 # splitpoint
    return op(treereduce(tree[:s], op, fn),
              treereduce(tree[s:], op, fn))

# chooses assignment of 32 bit or full 64 bit depending on is_32bit
def eq32(is_32bit, dest, src):
    return [dest[0:32].eq(src[0:32]),
            dest[32:64].eq(Mux(is_32bit, 0, src[32:64]))]


# a wrapper function formerly in run_simulation that is still useful.
# Simulation.add_sync_process now only takes functions, it does not
# take generators.  so passing in arguments is no longer possible.
# with this wrapper, the following is possible:
#       sim.add_sync_process(wrap.dut(parallel_sender_number=0))
#       sim.add_sync_process(wrap.dut(parallel_sender_number=1))

def wrap(process):
    def wrapper():
        yield from process
    return wrapper


# a "rising edge" generator.  can take signals of greater than width 1

def rising_edge(m, sig):
    delay = Signal.like(sig)
    rising = Signal.like(sig)
    delay.name = "%s_dly" % sig.name
    rising.name = "%s_rise" % sig.name
    m.d.sync += delay.eq(sig) # 1 clock delay
    m.d.comb += rising.eq(sig & ~delay) # sig is hi but delay-sig is lo
    return rising


# Display function (dummy if non-existent)
# added as a patch from jeanthom
# https://gist.githubusercontent.com/jeanthom/
#           f97f5b928720d4adda9d295e8a5bc078/
#           raw/694274e0aceec993c0fc127e296b1a85b93c1b89/nmigen-display.diff
try:
    from nmigen.hdl.ast import Display
except ImportError:
    def Display(*args):
        return []


def sel(m, r, sel_bits, field_width=None, name=None, src_loc_at=0):
    """Forms a subfield from a selection of bits of the signal `r`
    ("register").

    :param m: nMigen Module for adding the wires
    :param r: signal containing the field from which to select the subfield
    :param sel_bits: bit indices of the subfield, in "MSB 0" convention,
                     from most significant to least significant. Note that
                     the indices are allowed to be non-contiguous and/or
                     out-of-order.
    :param field_width: field width. If absent, use the signal `r` own width.
    :param name: name of the generated Signal
    :param src_loc_at: in the absence of `name`, stack level in which
                       to find it

    :returns: a new Signal which gets assigned to the subfield
    """
    # find the MSB index in LSB0 numbering
    if field_width is None:
        msb = len(r) - 1
    else:
        msb = field_width - 1
    # extract the selected bits
    sig_list = []
    for idx in sel_bits:
        sig_list.append(r[msb - idx])
    # place the LSB at the front of the list,
    # since, in nMigen, Cat starts from the LSB
    sig_list.reverse()
    sel_ret = Signal(len(sig_list), name=name, src_loc_at=src_loc_at+1)
    m.d.comb += sel_ret.eq(Cat(*sig_list))
    return sel_ret
