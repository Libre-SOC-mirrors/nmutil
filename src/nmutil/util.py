from collections.abc import Iterable
from nmigen import Mux, Signal

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

