"""
    This work is funded through NLnet under Grant 2019-02-012

    License: LGPLv3+


"""

from copy import copy
# this is a POWER ISA 3.0B compatible *signed* div function
# however it is also the c, c++, rust, java *and* x86 way of doing things


def trunc_divs(n, d):
    abs_n = abs(n.to_signed_int())
    abs_d = abs(d.to_signed_int())
    print("trunc_div n", abs_n, n.to_signed_int())
    print("trunc_div d", abs_d, d.to_signed_int())
    abs_q = abs_n // abs_d
    sign_n = n.value & (1 << (n.bits - 1)) != 0
    sign_d = d.value & (1 << (d.bits - 1)) != 0
    print("trunc_div", hex(n.value), hex(d.value),
          hex(abs_n), hex(abs_d), hex(abs_q),
          sign_n, sign_d)
    res = copy(n)
    if (sign_n == sign_d):
        res.value = abs_q
        if res.value & (1 << (res.bits - 1)) != 0:
            # result should be positive but is negative
            raise OverflowError()
        return res
    mask = (1 << res.bits) - 1
    res.value = (-abs_q) & mask

    return res


# this is a POWER ISA 3.0B compatible *signed* mod / remainder function
# however it is also the c, c++, rust, java *and* x86 way of doing things
def trunc_rems(n, d):
    m = d * trunc_divs(n, d)

    # cheat - really shouldn't do this. mul returns full length
    m.bits = n.bits
    return n - m
