from nmigen import Signal, Cat

# TODO: turn this into a module
def byte_reverse(m, name, data, length):
    """byte_reverse: unlike nmigen word_select this takes a dynamic length

    nmigen Signal.word_select may only take a fixed length.  we need
    bigendian byte-reverse, half-word reverse, word and dword reverse.
    """
    comb = m.d.comb
    data_r = Signal.like(data, name=name)

    if isinstance(length, int):
        j = length
        rev = []
        for i in range(j):
            dest = data_r.word_select(i, 8)
            res.append(data.word_select(j-1-i, 8))
        comb += data_r.eq(Cat(*rev))
        return data_r

    with m.Switch(length):
        for j in [1,2,4,8]:
            with m.Case(j):
                rev = []
                for i in range(j):
                    rev.append(data.word_select(j-1-i, 8))
                comb += data_r.eq(Cat(*rev))
    return data_r


