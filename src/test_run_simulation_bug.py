from nmigen import Signal, Module, Elaboratable
from nmigen.compat.sim import run_simulation

# test for https://github.com/nmigen/nmigen/issues/344


class MyModule(Elaboratable):
    def __init__(self):
        self.a = Signal()

    def elaborate(self, platform):
        m = Module()
        m.d.sync += self.a.eq(~self.a)
        return m


def test1():
    dut = MyModule()

    def generator():
        for _i in range(10):
            print((yield dut.a))
            yield

    run_simulation(dut, generator(),
                   vcd_name="test_run_simulation_bug.vcd")


if __name__ == '__main__':
    test1()
