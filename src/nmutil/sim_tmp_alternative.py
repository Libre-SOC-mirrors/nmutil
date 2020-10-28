"""Run-time selection of simulator engine

Usage::

    from nmutil.sim_tmp_alternative import Simulator

Then, use :py:class:`Simulator` as usual.

This should be backwards compatible to old developer versions of nMigen.

To use cxxsim, export ``NMIGEN_SIM_MODE=cxxsim`` from the shell.
Be sure to check out the ``cxxsim`` branch of nMigen, and update yosys
to the latest commit as well.

To use pysim, just keep ``NMIGEN_SIM_MODE`` unset.
Alternatively, export ``NMIGEN_SIM_MODE=pysim``.

Example::

    $ export NMIGEN_SIM_MODE=...  # pysim or cxxsim, default is pysim
    $ python ...

or, even::

    $ NMIGEN_SIM_MODE=...  python ...
"""

import os

try:
    from nmigen.sim import (Simulator as RealSimulator, Delay, Settle, Tick,
                            Passive)
    detected_new_api = True
except ImportError:
    detected_new_api = False
    try:
        from nmigen.sim.pysim import (Simulator as RealSimulator,
                                      Delay, Settle, Tick, Passive)
    except ImportError:
        from nmigen.back.pysim import (Simulator as RealSimulator,
                                       Delay, Settle, Tick, Passive)

nmigen_sim_environ_variable = os.environ.get("NMIGEN_SIM_MODE") \
                              or "pysim"
"""Detected run-time engine from environment"""


def Simulator(*args, **kwargs):
    """Wrapper that allows run-time selection of simulator engine"""
    if detected_new_api:
        kwargs['engine'] = nmigen_sim_environ_variable
    return RealSimulator(*args, **kwargs)


def is_engine_cxxsim():
    """Returns ``True`` if the selected engine is cxxsim"""
    return detected_new_api and nmigen_sim_environ_variable == "cxxsim"


def is_engine_pysim():
    """Returns ``True`` if the selected engine is pysim"""
    return not detected_new_api or nmigen_sim_environ_variable == "pysim"


nmigen_sim_top_module = "top." if is_engine_pysim() else ""
"""Work-around for cxxsim not defining the top-level module"""
