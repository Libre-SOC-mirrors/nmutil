# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2021 Jacob Lifshay

# Funded by NLnet Assure Programme 2021-02-052, https://nlnet.nl/assure part
# of Horizon 2020 EU Programme 957073.

from contextlib import contextmanager
from hashlib import sha256
from nmutil.get_test_path import get_test_path
from nmigen.sim import Simulator


def hash_256(v):
    return int.from_bytes(
        sha256(bytes(v, encoding='utf-8')).digest(),
        byteorder='little'
    )


@contextmanager
def do_sim(test_case, dut, traces=()):
    sim = Simulator(dut)
    path = get_test_path(test_case, "sim_test_out")
    path.parent.mkdir(parents=True, exist_ok=True)
    vcd_path = path.with_suffix(".vcd")
    gtkw_path = path.with_suffix(".gtkw")
    with sim.write_vcd(vcd_path.open("wt", encoding="utf-8"),
                       gtkw_path.open("wt", encoding="utf-8"),
                       traces=traces):
        yield sim
