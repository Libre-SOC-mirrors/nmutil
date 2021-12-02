import re
import shutil
import subprocess
import textwrap
import unittest
import warnings
from contextlib import contextmanager

from nmigen.hdl.ir import Fragment
from nmigen.back import rtlil
from nmigen._toolchain import require_tool

from nmutil.get_test_path import get_test_path


__all__ = ["FHDLTestCase"]


class FHDLTestCase(unittest.TestCase):
    def assertRepr(self, obj, repr_str):
        if isinstance(obj, list):
            obj = Statement.cast(obj)

        def prepare_repr(repr_str):
            repr_str = re.sub(r"\s+",   " ",  repr_str)
            repr_str = re.sub(r"\( (?=\()", "(", repr_str)
            repr_str = re.sub(r"\) (?=\))", ")", repr_str)
            return repr_str.strip()
        self.assertEqual(prepare_repr(repr(obj)), prepare_repr(repr_str))

    @contextmanager
    def assertRaises(self, exception, msg=None):
        with super().assertRaises(exception) as cm:
            yield
        if msg is not None:
            # WTF? unittest.assertRaises is completely broken.
            self.assertEqual(str(cm.exception), msg)

    @contextmanager
    def assertRaisesRegex(self, exception, regex=None):
        with super().assertRaises(exception) as cm:
            yield
        if regex is not None:
            # unittest.assertRaisesRegex also seems broken...
            self.assertRegex(str(cm.exception), regex)

    @contextmanager
    def assertWarns(self, category, msg=None):
        with warnings.catch_warnings(record=True) as warns:
            yield
        self.assertEqual(len(warns), 1)
        self.assertEqual(warns[0].category, category)
        if msg is not None:
            self.assertEqual(str(warns[0].message), msg)

    def assertFormal(self, spec, mode="bmc", depth=1, solver="",
                     base_path="formal_test_temp"):
        path = get_test_path(self, base_path)

        # The sby -f switch seems not fully functional when sby is
        # reading from stdin.
        shutil.rmtree(path, ignore_errors=True)
        path.mkdir(parents=True)

        if mode == "hybrid":
            # A mix of BMC and k-induction, as per personal
            # communication with Clifford Wolf.
            script = "setattr -unset init w:* a:nmigen.sample_reg %d"
            mode = "bmc"
        else:
            script = ""

        config = textwrap.dedent("""\
        [options]
        mode {mode}
        depth {depth}
        wait on

        [engines]
        smtbmc {solver}

        [script]
        read_ilang top.il
        prep
        {script}

        [file top.il]
        {rtlil}
        """).format(
            mode=mode,
            depth=depth,
            solver=solver,
            script=script,
            rtlil=rtlil.convert(Fragment.get(spec, platform="formal"))
        )
        with subprocess.Popen([require_tool("sby"), "-d", "job"],
                              cwd=path,
                              universal_newlines=True,
                              stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE) as proc:
            stdout, stderr = proc.communicate(config)
            if proc.returncode != 0:
                self.fail("Formal verification failed:\n" + stdout)
