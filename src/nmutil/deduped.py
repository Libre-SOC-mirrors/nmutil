import functools
import weakref


class _KeyBuilder:
    def __init__(self, do_delete):
        self.__keys = []
        self.__refs = {}
        self.__do_delete = do_delete

    def add_ref(self, v):
        v_id = id(v)
        if v_id in self.__refs:
            return
        try:
            v = weakref.ref(v, callback=self.__do_delete)
        except TypeError:
            pass
        self.__refs[v_id] = v

    def add(self, k, v):
        self.__keys.append(id(k))
        self.__keys.append(id(v))
        self.add_ref(k)
        self.add_ref(v)

    def finish(self):
        return tuple(self.__keys), tuple(self.__refs.values())


def deduped(*, global_keys=()):
    """decorator that causes functions to deduplicate their results based on
    their input args and the requested globals. For each set of arguments, it
    will always return the exact same object, by storing it internally.
    Arguments are compared by their identity, so they don't need to be
    hashable.

    Usage:
    ```
    # for functions that don't depend on global variables
    @deduped()
    def my_fn1(a, b, *, c=1):
        return a + b * c

    my_global = 23

    # for functions that depend on global variables
    @deduped(global_keys=[lambda: my_global])
    def my_fn2(a, b, *, c=2):
        return a + b * c + my_global
    ```
    """
    global_keys = tuple(global_keys)
    assert all(map(callable, global_keys))

    def decorator(f):
        if isinstance(f, (staticmethod, classmethod)):
            raise TypeError("@staticmethod or @classmethod should be applied "
                            "to the result of @deduped, not the other way"
                            " around")
        assert callable(f)

        map = {}

        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            key_builder = _KeyBuilder(lambda _: map.pop(key, None))
            for arg in args:
                key_builder.add(None, arg)
            for k, v in kwargs.items():
                key_builder.add(k, v)
            for global_key in global_keys:
                key_builder.add(None, global_key())
            key, refs = key_builder.finish()
            if key in map:
                return map[key][0]
            retval = f(*args, **kwargs)
            # keep reference to stuff used for key to avoid ids
            # getting reused for something else.
            map[key] = retval, refs
            return retval
        return wrapper
    return decorator
