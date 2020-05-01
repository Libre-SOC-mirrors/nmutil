from collections.abc import Iterable

# XXX this already exists in nmigen._utils
# see https://bugs.libre-soc.org/show_bug.cgi?id=297
def flatten(v):
    if isinstance(v, Iterable):
        for i in v:
            yield from flatten(i)
    else:
        yield v
