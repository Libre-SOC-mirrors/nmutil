from nmigen import Signal

# TODO: turn this into a module
def byte_reverse(m, name, data, length):
    """byte_reverse: unlike nmigen word_select this takes a dynamic length

    nmigen Signal.word_select may only take a fixed length.  we need
    bigendian byte-reverse, half-word reverse, word and dword reverse.
    """
    comb = m.d.comb
    data_r = Signal.like(data, name=name)
    with m.Switch(length):
        for j in [1,2,4,8]:
            with m.Case(j):
                for i in range(j):
                    dest = data_r.word_select(i, 8)
                    src = data.word_select(j-1-i, 8)
                    comb += dest.eq(src)
    return data_r


