import unittest
from nmutil.deduped import deduped


class TestDeduped(unittest.TestCase):
    def test_deduped1(self):
        global_key = 1
        call_count = 0

        def call_counter():
            nonlocal call_count
            retval = call_count
            call_count += 1
            return retval

        class C:
            def __init__(self, name):
                self.name = name

            @deduped()
            def method(self, a, *, b=1):
                return self, a, b, call_counter()

            @deduped(global_keys=[lambda: global_key])
            def method_with_global(self, a, *, b=1):
                return self, a, b, call_counter(), global_key

            @staticmethod
            @deduped()
            def smethod(a, *, b=1):
                return a, b, call_counter()

            @classmethod
            @deduped()
            def cmethod(cls, a, *, b=1):
                return cls, a, b, call_counter()

            def __repr__(self):
                return f"{self.__class__.__name__}({self.name})"

        class D(C):
            pass

        c1 = C("c1")
        c2 = C("c2")

        # run everything twice to ensure caching works
        for which_pass in ("first", "second"):
            with self.subTest(which_pass=which_pass):
                self.assertEqual(C.cmethod(1), (C, 1, 1, 0))
                self.assertEqual(C.cmethod(2), (C, 2, 1, 1))
                self.assertEqual(C.cmethod(1, b=5), (C, 1, 5, 2))
                self.assertEqual(D.cmethod(1, b=5), (D, 1, 5, 3))
                self.assertEqual(D.smethod(1, b=5), (1, 5, 4))
                self.assertEqual(C.smethod(1, b=5), (1, 5, 4))
                self.assertEqual(c1.method(None), (c1, None, 1, 5))
                global_key = 2
                self.assertEqual(c1.cmethod(1, b=5), (C, 1, 5, 2))
                self.assertEqual(c1.smethod(1, b=5), (1, 5, 4))
                self.assertEqual(c1.method(1, b=5), (c1, 1, 5, 6))
                self.assertEqual(c2.method(1, b=5), (c2, 1, 5, 7))
                self.assertEqual(c1.method_with_global(1), (c1, 1, 1, 8, 2))
                global_key = 1
                self.assertEqual(c1.cmethod(1, b=5), (C, 1, 5, 2))
                self.assertEqual(c1.smethod(1, b=5), (1, 5, 4))
                self.assertEqual(c1.method(1, b=5), (c1, 1, 5, 6))
                self.assertEqual(c2.method(1, b=5), (c2, 1, 5, 7))
                self.assertEqual(c1.method_with_global(1), (c1, 1, 1, 9, 1))
        self.assertEqual(call_count, 10)

    def test_bad_methods(self):
        with self.assertRaisesRegex(TypeError,
                                    ".*@staticmethod.*applied.*@deduped.*"):
            class C:
                @deduped()
                @staticmethod
                def f():
                    pass

        with self.assertRaisesRegex(TypeError,
                                    ".*@classmethod.*applied.*@deduped.*"):
            class C:
                @deduped()
                @classmethod
                def f():
                    pass


if __name__ == '__main__':
    unittest.main()
