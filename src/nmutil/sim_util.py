# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2021 Jacob Lifshay

# Funded by NLnet Assure Programme 2021-02-052, https://nlnet.nl/assure part
# of Horizon 2020 EU Programme 957073.

from contextlib import contextmanager
from hashlib import sha256

from nmigen.hdl.ir import Fragment, ClockDomain
from nmutil.get_test_path import get_test_path
from nmigen.sim import Simulator
from nmigen.back.rtlil import convert


def hash_256(v):
    return int.from_bytes(
        sha256(bytes(v, encoding='utf-8')).digest(),
        byteorder='little'
    )


def write_il(test_case, dut, ports=()):
    # only elaborate once, cuz users' stupid code breaks if elaborating twice
    dut = Fragment.get(dut, platform=None)
    if "sync" not in dut.domains:
        dut.add_domains(ClockDomain("sync"))
    path = get_test_path(test_case, "sim_test_out")
    path.parent.mkdir(parents=True, exist_ok=True)
    il_path = path.with_suffix(".il")
    il_path.write_text(convert(dut, ports=ports), encoding="utf-8")
    return dut, path


@contextmanager
def do_sim(test_case, dut, traces=(), ports=None):
    if ports is None:
        ports = traces
    dut, path = write_il(test_case, dut, ports)
    sim = Simulator(dut)
    vcd_path = path.with_suffix(".vcd")
    gtkw_path = path.with_suffix(".gtkw")
    with sim.write_vcd(vcd_path.open("wt", encoding="utf-8"),
                       gtkw_path.open("wt", encoding="utf-8"),
                       traces=traces):
        yield sim
