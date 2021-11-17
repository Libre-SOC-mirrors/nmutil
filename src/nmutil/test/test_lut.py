# SPDX-License-Identifier: LGPL-3-or-later
# See Notices.txt for copyright information

from contextlib import contextmanager
import unittest
from hashlib import sha256
import shutil
import subprocess
from nmigen.back import rtlil
import textwrap
from nmigen.hdl.ast import AnyConst, Assert, Signal
from nmigen.hdl.dsl import Module
from nmigen.hdl.ir import Fragment
from nmutil.get_test_path import get_test_path
from nmutil.lut import BitwiseMux, BitwiseLut, TreeBitwiseLut
from nmigen.sim import Simulator, Delay


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


# copied from ieee754fpu/src/ieee754/partitioned_signal_tester.py
def formal(test_case, hdl, *, base_path="formal_test_temp"):
    hdl = Fragment.get(hdl, platform="formal")
    path = get_test_path(test_case, base_path)
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True)
    sby_name = "config.sby"
    sby_file = path / sby_name

    sby_file.write_text(textwrap.dedent(f"""\
    [options]
    mode prove
    depth 1
    wait on

    [engines]
    smtbmc

    [script]
    read_rtlil top.il
    prep

    [file top.il]
    {rtlil.convert(hdl)}
    """), encoding="utf-8")
    sby = shutil.which('sby')
    assert sby is not None
    with subprocess.Popen(
        [sby, sby_name],
        cwd=path, text=True, encoding="utf-8",
        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE
    ) as p:
        stdout, stderr = p.communicate()
        if p.returncode != 0:
            test_case.fail(f"Formal failed:\n{stdout}")


def hash_256(v):
    return int.from_bytes(
        sha256(bytes(v, encoding='utf-8')).digest(),
        byteorder='little'
    )


class TestBitwiseMux(unittest.TestCase):
    def test(self):
        width = 2
        dut = BitwiseMux(width)

        def case(sel, t, f, expected):
            with self.subTest(sel=bin(sel), t=bin(t), f=bin(f)):
                yield dut.sel.eq(sel)
                yield dut.t.eq(t)
                yield dut.f.eq(f)
                yield Delay(1e-6)
                output = yield dut.output
                with self.subTest(output=bin(output), expected=bin(expected)):
                    self.assertEqual(expected, output)

        def process():
            for sel in range(2 ** width):
                for t in range(2 ** width):
                    for f in range(2**width):
                        expected = 0
                        for i in range(width):
                            if sel & 2 ** i:
                                if t & 2 ** i:
                                    expected |= 2 ** i
                            elif f & 2 ** i:
                                expected |= 2 ** i
                        yield from case(sel, t, f, expected)
        with do_sim(self, dut, [dut.sel, dut.t, dut.f, dut.output]) as sim:
            sim.add_process(process)
            sim.run()

    def test_formal(self):
        width = 2
        dut = BitwiseMux(width)
        m = Module()
        m.submodules.dut = dut
        m.d.comb += dut.sel.eq(AnyConst(width))
        m.d.comb += dut.f.eq(AnyConst(width))
        m.d.comb += dut.t.eq(AnyConst(width))
        for i in range(width):
            with m.If(dut.sel[i]):
                m.d.comb += Assert(dut.t[i] == dut.output[i])
            with m.Else():
                m.d.comb += Assert(dut.f[i] == dut.output[i])
        formal(self, m)


class TestBitwiseLut(unittest.TestCase):
    def tst(self, cls):
        dut = cls(3, 16)
        mask = 2 ** dut.width - 1
        lut_mask = 2 ** dut.lut.width - 1
        if cls is TreeBitwiseLut:
            mux_inputs = {k: s.name for k, s in dut._mux_inputs.items()}
            self.assertEqual(mux_inputs, {
                (): 'mux_input_0bxxx',
                (False,): 'mux_input_0bxx0',
                (False, False): 'mux_input_0bx00',
                (False, False, False): 'mux_input_0b000',
                (False, False, True): 'mux_input_0b100',
                (False, True): 'mux_input_0bx10',
                (False, True, False): 'mux_input_0b010',
                (False, True, True): 'mux_input_0b110',
                (True,): 'mux_input_0bxx1',
                (True, False): 'mux_input_0bx01',
                (True, False, False): 'mux_input_0b001',
                (True, False, True): 'mux_input_0b101',
                (True, True): 'mux_input_0bx11',
                (True, True, False): 'mux_input_0b011',
                (True, True, True): 'mux_input_0b111'
            })

        def case(in0, in1, in2, lut):
            expected = 0
            for i in range(dut.width):
                lut_index = 0
                if in0 & 2 ** i:
                    lut_index |= 2 ** 0
                if in1 & 2 ** i:
                    lut_index |= 2 ** 1
                if in2 & 2 ** i:
                    lut_index |= 2 ** 2
                if lut & 2 ** lut_index:
                    expected |= 2 ** i
            with self.subTest(in0=bin(in0), in1=bin(in1), in2=bin(in2),
                              lut=bin(lut)):
                yield dut.inputs[0].eq(in0)
                yield dut.inputs[1].eq(in1)
                yield dut.inputs[2].eq(in2)
                yield dut.lut.eq(lut)
                yield Delay(1e-6)
                output = yield dut.output
                with self.subTest(output=bin(output), expected=bin(expected)):
                    self.assertEqual(expected, output)

        def process():
            for case_index in range(100):
                with self.subTest(case_index=case_index):
                    in0 = hash_256(f"{case_index} in0") & mask
                    in1 = hash_256(f"{case_index} in1") & mask
                    in2 = hash_256(f"{case_index} in2") & mask
                    lut = hash_256(f"{case_index} lut") & lut_mask
                    yield from case(in0, in1, in2, lut)
        with do_sim(self, dut, [*dut.inputs, dut.lut, dut.output]) as sim:
            sim.add_process(process)
            sim.run()

    def tst_formal(self, cls):
        dut = cls(3, 16)
        m = Module()
        m.submodules.dut = dut
        m.d.comb += dut.inputs[0].eq(AnyConst(dut.width))
        m.d.comb += dut.inputs[1].eq(AnyConst(dut.width))
        m.d.comb += dut.inputs[2].eq(AnyConst(dut.width))
        m.d.comb += dut.lut.eq(AnyConst(dut.lut.width))
        for i in range(dut.width):
            lut_index = Signal(dut.input_count, name=f"lut_index_{i}")
            for j in range(dut.input_count):
                m.d.comb += lut_index[j].eq(dut.inputs[j][i])
            for j in range(dut.lut.width):
                with m.If(lut_index == j):
                    m.d.comb += Assert(dut.lut[j] == dut.output[i])
        formal(self, m)

    def test(self):
        self.tst(BitwiseLut)

    def test_tree(self):
        self.tst(TreeBitwiseLut)

    def test_formal(self):
        self.tst_formal(BitwiseLut)

    def test_tree_formal(self):
        self.tst_formal(TreeBitwiseLut)


if __name__ == "__main__":
    unittest.main()
