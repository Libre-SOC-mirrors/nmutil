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
