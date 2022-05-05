from nmigen.sim import Delay
from nmutil.clz import CLZ, clz
from nmutil.sim_util import do_sim
import unittest


def reference_clz(v, width):
    assert isinstance(width, int) and 0 <= width
    assert isinstance(v, int) and 0 <= v < 1 << width
    msb = 1 << (width - 1)
    retval = 0
    while retval < width:
        if v & msb:
            break
        v <<= 1
        retval += 1
    return retval


class TestCLZ(unittest.TestCase):
    def tst(self, width):
        assert isinstance(width, int) and 0 <= width
        dut = CLZ(width)

        def process():
            for inp in range(1 << width):
                expected = reference_clz(inp, width)
                with self.subTest(inp=hex(inp), expected=expected):
                    yield dut.sig_in.eq(inp)
                    yield Delay(1e-6)
                    sim_lz = yield dut.lz
                    py_lz = clz(inp, width)
                    with self.subTest(sim_lz=sim_lz, py_lz=py_lz):
                        self.assertEqual(sim_lz, expected)
                        self.assertEqual(py_lz, expected)
        with do_sim(self, dut, [dut.sig_in, dut.lz]) as sim:
            sim.add_process(process)
            sim.run()

    def test_1(self):
        self.tst(1)

    def test_2(self):
        self.tst(2)

    def test_3(self):
        self.tst(3)

    def test_4(self):
        self.tst(4)

    def test_5(self):
        self.tst(5)

    def test_6(self):
        self.tst(6)

    def test_7(self):
        self.tst(7)

    def test_8(self):
        self.tst(8)

    def test_9(self):
        self.tst(9)

    def test_10(self):
        self.tst(10)

    def test_11(self):
        self.tst(11)

    def test_12(self):
        self.tst(12)


if __name__ == "__main__":
    unittest.main()
