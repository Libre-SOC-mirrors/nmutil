"""
    This work is funded through NLnet under Grant 2019-02-012

    License: LGPLv3+


"""
from nmigen import Repl, Cat, Const


def exts(exts_data, width, fullwidth):
    exts_data = exts_data[0:width]
    topbit = exts_data[-1]
    signbits = Repl(topbit, fullwidth-width)
    return Cat(exts_data, signbits)


def extz(exts_data, width, fullwidth):
    exts_data = exts_data[0:width]
    topbit = Const(0)
    signbits = Repl(topbit, fullwidth-width)
    return Cat(exts_data, signbits)


