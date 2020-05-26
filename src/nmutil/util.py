from collections.abc import Iterable

# XXX this already exists in nmigen._utils
# see https://bugs.libre-soc.org/show_bug.cgi?id=297
def flatten(v):
    if isinstance(v, Iterable):
        for i in v:
            yield from flatten(i)
    else:
        yield v

# tree reduction function.  operates recursively.
def treereduce(tree, op, attr="data_o"):
    #print ("treereduce", tree)
    if not isinstance(tree, list):
        return tree
    if len(tree) == 1:
        return getattr(tree[0], attr)
    if len(tree) == 2:
        return op(getattr(tree[0], attr), getattr(tree[1], attr))
    s = len(tree) // 2 # splitpoint
    return treereduce(op(tree[:s], op, attr), treereduce(tree[s:], op, attr))
