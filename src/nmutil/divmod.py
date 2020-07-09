# this is a POWER ISA 3.0B compatible div function
# however it is also the c, c++, rust, java *and* x86 way of doing things
def trunc_div(n, d):
    abs_n = abs(n)
    abs_d = abs(d)
    abs_q = abs_n // abs_d
    #print ("trunc_div", n.value, d.value,
    #                    abs_n.value, abs_d.value, abs_q.value,
    #                    n == abs_n, d == abs_d)
    if (n == abs_n) == (d == abs_d):
        return abs_q
    return -abs_q


# this is a POWER ISA 3.0B compatible mod / remainder function
# however it is also the c, c++, rust, java *and* x86 way of doing things
def trunc_rem(n, d):
    return n - d * trunc_div(n, d)


