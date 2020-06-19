# this is a POWER ISA 3.0B compatible div function
# however it is also the c, c++, rust, java *and* x86 way of doing things
def trunc_div(n, d):
    abs_n = abs(n)
    abs_d = abs(d)
    abs_q = n // d
    if (n < 0) == (d < 0):
        return abs_q
    return -abs_q


# this is a POWER ISA 3.0B compatible mod / remainder function
# however it is also the c, c++, rust, java *and* x86 way of doing things
def trunc_rem(n, d):
    return n - d * trunc_div(n, d)


