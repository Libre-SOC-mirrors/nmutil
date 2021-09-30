# Copyright (C) Luke Kenneth Casson Leighton 2020,2021 <lkcl@lkcl.net>
# License: LGPLv2+
"""
Provides sign/unsigned extension/truncation utility functions.

This work is funded through NLnet under Grant 2019-02-012
"""
from nmigen import Repl, Cat, Const


def exts(exts_data, width, fullwidth):
    diff = fullwidth-width
    if diff == 0:
        return exts_data
    exts_data = exts_data[0:width]
    if diff <= 0:
        return exts_data[:fullwidth]
    topbit = exts_data[-1]
    signbits = Repl(topbit, diff)
    return Cat(exts_data, signbits)


def extz(extz_data, width, fullwidth):
    diff = fullwidth-width
    if diff == 0:
        return extz_data
    extz_data = extz_data[0:width]
    if diff <= 0:
        return extz_data[:fullwidth]
    topbit = Const(0)
    signbits = Repl(topbit, diff)
    return Cat(extz_data, signbits)


def ext(data, shape, newwidth):
    """extend/truncate data to new width, preserving sign
    """
    width, signed = shape
    if signed:
        return exts(data, width, newwidth)
    return extz(data, width, newwidth)
