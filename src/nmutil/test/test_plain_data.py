# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2022 Jacob Lifshay programmerjake@gmail.com

import unittest
from nmutil.plain_data import FrozenPlainDataError, plain_data


@plain_data()
class PlainData0:
    __slots__ = ()


@plain_data()
class PlainData1:
    __slots__ = "a", "b", "x", "y"

    def __init__(self, a, b, *, x, y):
        self.a = a
        self.b = b
        self.x = x
        self.y = y


@plain_data()
class PlainData2(PlainData1):
    __slots__ = "a", "z"

    def __init__(self, a, b, *, x, y, z):
        super().__init__(a, b, x=x, y=y)
        self.z = z


@plain_data(frozen=True, unsafe_hash=True)
class PlainDataF0:
    __slots__ = ()


@plain_data(frozen=True, unsafe_hash=True)
class PlainDataF1:
    __slots__ = "a", "b", "x", "y"

    def __init__(self, a, b, *, x, y):
        self.a = a
        self.b = b
        self.x = x
        self.y = y


class TestPlainData(unittest.TestCase):
    def test_repr(self):
        self.assertEqual(repr(PlainData0()), "PlainData0()")
        self.assertEqual(repr(PlainData1(1, 2, x="x", y="y")),
                         "PlainData1(a=1, b=2, x='x', y='y')")
        self.assertEqual(repr(PlainData2(1, 2, x="x", y="y", z=3)),
                         "PlainData2(a=1, b=2, x='x', y='y', z=3)")

    def test_eq(self):
        self.assertTrue(PlainData0() == PlainData0())
        self.assertFalse('a' == PlainData0())
        self.assertTrue(PlainData1(1, 2, x="x", y="y")
                        == PlainData1(1, 2, x="x", y="y"))
        self.assertFalse(PlainData1(1, 2, x="x", y="y")
                         == PlainData1(1, 2, x="x", y="z"))
        self.assertFalse(PlainData1(1, 2, x="x", y="y")
                         == PlainData2(1, 2, x="x", y="y", z=3))

    def test_frozen(self):
        not_frozen = PlainData0()
        not_frozen.a = 1
        frozen0 = PlainDataF0()
        with self.assertRaises(AttributeError):
            frozen0.a = 1
        frozen1 = PlainDataF1(1, 2, x="x", y="y")
        with self.assertRaises(FrozenPlainDataError):
            frozen1.a = 1

    # FIXME: add more tests


if __name__ == "__main__":
    unittest.main()
