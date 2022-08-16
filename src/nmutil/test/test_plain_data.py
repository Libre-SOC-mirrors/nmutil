# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2022 Jacob Lifshay programmerjake@gmail.com

import operator
import pickle
import unittest
from nmutil.plain_data import (FrozenPlainDataError, plain_data,
                               fields, replace)


@plain_data(order=True)
class PlainData0:
    __slots__ = ()


@plain_data(order=True)
class PlainData1:
    __slots__ = "a", "b", "x", "y"

    def __init__(self, a, b, *, x, y):
        self.a = a
        self.b = b
        self.x = x
        self.y = y


@plain_data(order=True)
class PlainData2(PlainData1):
    __slots__ = "a", "z"

    def __init__(self, a, b, *, x, y, z):
        super().__init__(a, b, x=x, y=y)
        self.z = z


@plain_data(order=True, frozen=True, unsafe_hash=True)
class PlainDataF0:
    __slots__ = ()


@plain_data(order=True, frozen=True, unsafe_hash=True)
class PlainDataF1:
    __slots__ = "a", "b", "x", "y"

    def __init__(self, a, b, *, x, y):
        self.a = a
        self.b = b
        self.x = x
        self.y = y


@plain_data(order=True, frozen=True, unsafe_hash=True)
class PlainDataF2(PlainDataF1):
    __slots__ = "a", "z"

    def __init__(self, a, b, *, x, y, z):
        super().__init__(a, b, x=x, y=y)
        self.z = z


@plain_data()
class UnsetField:
    __slots__ = "a", "b"

    def __init__(self, **kwargs):
        for name, value in kwargs.items():
            setattr(self, name, value)


class TestPlainData(unittest.TestCase):
    def test_fields(self):
        self.assertEqual(fields(PlainData0), ())
        self.assertEqual(fields(PlainData0()), ())
        self.assertEqual(fields(PlainData1), ("a", "b", "x", "y"))
        self.assertEqual(fields(PlainData1(1, 2, x="x", y="y")),
                         ("a", "b", "x", "y"))
        self.assertEqual(fields(PlainData2), ("a", "b", "x", "y", "z"))
        self.assertEqual(fields(PlainData2(1, 2, x="x", y="y", z=3)),
                         ("a", "b", "x", "y", "z"))
        self.assertEqual(fields(PlainDataF0), ())
        self.assertEqual(fields(PlainDataF0()), ())
        self.assertEqual(fields(PlainDataF1), ("a", "b", "x", "y"))
        self.assertEqual(fields(PlainDataF1(1, 2, x="x", y="y")),
                         ("a", "b", "x", "y"))
        self.assertEqual(fields(PlainDataF2), ("a", "b", "x", "y", "z"))
        self.assertEqual(fields(PlainDataF2(1, 2, x="x", y="y", z=3)),
                         ("a", "b", "x", "y", "z"))
        with self.assertRaisesRegex(
                TypeError,
                r"the passed-in object must be a class or an instance of a "
                r"class decorated with @plain_data\(\)"):
            fields(type)

    def test_replace(self):
        with self.assertRaisesRegex(
                TypeError,
                r"the passed-in object must be a class or an instance of a "
                r"class decorated with @plain_data\(\)"):
            replace(PlainData0)
        with self.assertRaisesRegex(TypeError, "can't set unknown field 'a'"):
            replace(PlainData0(), a=1)
        with self.assertRaisesRegex(TypeError, "can't set unknown field 'z'"):
            replace(PlainDataF1(1, 2, x="x", y="y"), a=3, z=1)
        self.assertEqual(replace(PlainData0()), PlainData0())
        self.assertEqual(replace(PlainDataF1(1, 2, x="x", y="y")),
                         PlainDataF1(1, 2, x="x", y="y"))
        self.assertEqual(replace(PlainDataF1(1, 2, x="x", y="y"), a=3),
                         PlainDataF1(3, 2, x="x", y="y"))
        self.assertEqual(replace(PlainDataF1(1, 2, x="x", y="y"), x=5, a=3),
                         PlainDataF1(3, 2, x=5, y="y"))

    def test_eq(self):
        self.assertTrue(PlainData0() == PlainData0())
        self.assertFalse('a' == PlainData0())
        self.assertFalse(PlainDataF0() == PlainData0())
        self.assertTrue(PlainData1(1, 2, x="x", y="y")
                        == PlainData1(1, 2, x="x", y="y"))
        self.assertFalse(PlainData1(1, 2, x="x", y="y")
                         == PlainData1(1, 2, x="x", y="z"))
        self.assertFalse(PlainData1(1, 2, x="x", y="y")
                         == PlainData2(1, 2, x="x", y="y", z=3))

    def test_hash(self):
        def check_op(v, tuple_v):
            with self.subTest(v=v, tuple_v=tuple_v):
                self.assertEqual(hash(v), hash(tuple_v))

        def check(a, b, x, y, z):
            tuple_v = a, b, x, y, z
            v = PlainDataF2(a=a, b=b, x=x, y=y, z=z)
            check_op(v, tuple_v)

        check(1, 2, "x", "y", "z")

        check(1, 2, "x", "y", "a")
        check(1, 2, "x", "y", "zz")

        check(1, 2, "x", "a", "z")
        check(1, 2, "x", "zz", "z")

        check(1, 2, "a", "y", "z")
        check(1, 2, "zz", "y", "z")

        check(1, -10, "x", "y", "z")
        check(1, 10, "x", "y", "z")

        check(-10, 2, "x", "y", "z")
        check(10, 2, "x", "y", "z")

    def test_order(self):
        def check_op(l, r, tuple_l, tuple_r, op):
            with self.subTest(l=l, r=r,
                              tuple_l=tuple_l, tuple_r=tuple_r, op=op):
                self.assertEqual(op(l, r), op(tuple_l, tuple_r))
                self.assertEqual(op(r, l), op(tuple_r, tuple_l))

        def check(a, b, x, y, z):
            tuple_l = 1, 2, "x", "y", "z"
            l = PlainData2(a=1, b=2, x="x", y="y", z="z")
            tuple_r = a, b, x, y, z
            r = PlainData2(a=a, b=b, x=x, y=y, z=z)
            check_op(l, r, tuple_l, tuple_r, operator.eq)
            check_op(l, r, tuple_l, tuple_r, operator.ne)
            check_op(l, r, tuple_l, tuple_r, operator.lt)
            check_op(l, r, tuple_l, tuple_r, operator.le)
            check_op(l, r, tuple_l, tuple_r, operator.gt)
            check_op(l, r, tuple_l, tuple_r, operator.ge)

        check(1, 2, "x", "y", "z")

        check(1, 2, "x", "y", "a")
        check(1, 2, "x", "y", "zz")

        check(1, 2, "x", "a", "z")
        check(1, 2, "x", "zz", "z")

        check(1, 2, "a", "y", "z")
        check(1, 2, "zz", "y", "z")

        check(1, -10, "x", "y", "z")
        check(1, 10, "x", "y", "z")

        check(-10, 2, "x", "y", "z")
        check(10, 2, "x", "y", "z")

    def test_repr(self):
        self.assertEqual(repr(PlainData0()), "PlainData0()")
        self.assertEqual(repr(PlainData1(1, 2, x="x", y="y")),
                         "PlainData1(a=1, b=2, x='x', y='y')")
        self.assertEqual(repr(PlainData2(1, 2, x="x", y="y", z=3)),
                         "PlainData2(a=1, b=2, x='x', y='y', z=3)")
        self.assertEqual(repr(PlainDataF2(1, 2, x="x", y="y", z=3)),
                         "PlainDataF2(a=1, b=2, x='x', y='y', z=3)")
        self.assertEqual(repr(UnsetField()),
                         "UnsetField(a=<not set>, b=<not set>)")
        self.assertEqual(repr(UnsetField(a=2)), "UnsetField(a=2, b=<not set>)")
        self.assertEqual(repr(UnsetField(b=3)), "UnsetField(a=<not set>, b=3)")
        self.assertEqual(repr(UnsetField(a=5, b=3)), "UnsetField(a=5, b=3)")

    def test_frozen(self):
        not_frozen = PlainData0()
        not_frozen.a = 1
        frozen0 = PlainDataF0()
        with self.assertRaises(AttributeError):
            frozen0.a = 1
        frozen1 = PlainDataF1(1, 2, x="x", y="y")
        with self.assertRaises(FrozenPlainDataError):
            frozen1.a = 1

    def test_pickle(self):
        def check(v):
            with self.subTest(v=v):
                self.assertEqual(v, pickle.loads(pickle.dumps(v)))

        check(PlainData0())
        check(PlainData1(a=1, b=2, x="x", y="y"))
        check(PlainData2(a=1, b=2, x="x", y="y", z="z"))
        check(PlainDataF0())
        check(PlainDataF1(a=1, b=2, x="x", y="y"))
        check(PlainDataF2(a=1, b=2, x="x", y="y", z="z"))


if __name__ == "__main__":
    unittest.main()
