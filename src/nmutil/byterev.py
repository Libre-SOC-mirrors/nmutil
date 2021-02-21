"""
    This work is funded through NLnet under Grant 2019-02-012

    License: LGPLv3+
"""

from nmigen import Signal, Cat

# TODO: turn this into a module?
def byte_reverse(m, name, data, length):
    """byte_reverse: unlike nmigen word_select this takes a dynamic length

    nmigen Signal.word_select may only take a fixed length.  we need
    bigendian byte-reverse, half-word reverse, word and dword reverse.
    """
    comb = m.d.comb
    data_r = Signal.like(data, name=name)

    # if length is a static integer, we do not require a Case statement
    if isinstance(length, int):
        j = length
        rev = []
        for i in range(j):
            dest = data_r.word_select(i, 8)
            rev.append(data.word_select(j-1-i, 8))
        comb += data_r.eq(Cat(*rev))
        return data_r

    # Switch statement needed: dynamic length had better be = 1,2,4 or 8
    with m.Switch(length):
        for j in [1,2,4,8]:
            with m.Case(j):
                rev = []
                for i in range(j):
                    rev.append(data.word_select(j-1-i, 8))
                comb += data_r.eq(Cat(*rev))
    return data_r

