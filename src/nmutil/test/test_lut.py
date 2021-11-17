# SPDX-License-Identifier: LGPL-3-or-later
# See Notices.txt for copyright information

from contextlib import contextmanager
import unittest

from hashlib import sha256
from nmutil.get_test_path import get_test_path
from nmutil.lut import BitwiseMux, BitwiseLut
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


class TestBitwiseLut(unittest.TestCase):
    def test(self):
        dut = BitwiseLut(3, 16)
        mask = 2 ** dut.width - 1
        lut_mask = 2 ** dut.lut.width - 1
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


if __name__ == "__main__":
    unittest.main()
