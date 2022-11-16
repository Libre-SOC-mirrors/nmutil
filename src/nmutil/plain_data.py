# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2022 Jacob Lifshay programmerjake@gmail.com
import keyword


class FrozenPlainDataError(AttributeError):
    pass


class __NotSet:
    """ helper for __repr__ for when fields aren't set """

    def __repr__(self):
        return "<not set>"


__NOT_SET = __NotSet()


def __ignored_classes():
    classes = [object]  # type: list[type]

    from abc import ABC

    classes += [ABC]

    from typing import (
        Generic, SupportsAbs, SupportsBytes, SupportsComplex, SupportsFloat,
        SupportsInt, SupportsRound)

    classes += [
        Generic, SupportsAbs, SupportsBytes, SupportsComplex, SupportsFloat,
        SupportsInt, SupportsRound]

    from collections.abc import (
        Awaitable, Coroutine, AsyncIterable, AsyncIterator, AsyncGenerator,
        Hashable, Iterable, Iterator, Generator, Reversible, Sized, Container,
        Callable, Collection, Set, MutableSet, Mapping, MutableMapping,
        MappingView, KeysView, ItemsView, ValuesView, Sequence,
        MutableSequence)

    classes += [
        Awaitable, Coroutine, AsyncIterable, AsyncIterator, AsyncGenerator,
        Hashable, Iterable, Iterator, Generator, Reversible, Sized, Container,
        Callable, Collection, Set, MutableSet, Mapping, MutableMapping,
        MappingView, KeysView, ItemsView, ValuesView, Sequence,
        MutableSequence]

    # rest aren't supported by python 3.7, so try to import them and skip if
    # that errors

    try:
        # typing_extensions uses typing.Protocol if available
        from typing_extensions import Protocol
        classes.append(Protocol)
    except ImportError:
        pass

    for cls in classes:
        yield from cls.__mro__


__IGNORED_CLASSES = frozenset(__ignored_classes())


def _decorator(cls, *, eq, unsafe_hash, order, repr_, frozen):
    if not isinstance(cls, type):
        raise TypeError(
            "plain_data() can only be used as a class decorator")
    # slots is an ordered set by using dict keys.
    # always add __dict__ and __weakref__
    slots = {"__dict__": None, "__weakref__": None}
    if frozen:
        slots["__plain_data_init_done"] = None
    fields = []
    any_parents_have_dict = False
    any_parents_have_weakref = False
    for cur_cls in reversed(cls.__mro__):
        d = getattr(cur_cls, "__dict__", {})
        if cur_cls is not cls:
            if "__dict__" in d:
                any_parents_have_dict = True
            if "__weakref__" in d:
                any_parents_have_weakref = True
        if cur_cls in __IGNORED_CLASSES:
            continue
        try:
            cur_slots = cur_cls.__slots__
        except AttributeError as e:
            raise TypeError(f"{cur_cls.__module__}.{cur_cls.__qualname__}"
                            " must have __slots__ so plain_data() can "
                            "determine what fields exist in "
                            f"{cls.__module__}.{cls.__qualname__}") from e
        if not isinstance(cur_slots, tuple):
            raise TypeError("plain_data() requires __slots__ to be a "
                            "tuple of str")
        for field in cur_slots:
            if not isinstance(field, str):
                raise TypeError("plain_data() requires __slots__ to be a "
                                "tuple of str")
            if not field.isidentifier() or keyword.iskeyword(field):
                raise TypeError(
                    "plain_data() requires __slots__ entries to be valid "
                    "Python identifiers and not keywords")
            if field not in slots:
                fields.append(field)
            slots[field] = None

    fields = tuple(fields)  # fields needs to be immutable

    if any_parents_have_dict:
        # work around a CPython bug that unnecessarily checks if parent
        # classes already have the __dict__ slot.
        del slots["__dict__"]

    if any_parents_have_weakref:
        # work around a CPython bug that unnecessarily checks if parent
        # classes already have the __weakref__ slot.
        del slots["__weakref__"]

    # now create a new class having everything we need
    retval_dict = dict(cls.__dict__)
    # remove all old descriptors:
    for name in slots.keys():
        retval_dict.pop(name, None)

    retval_dict["__plain_data_fields"] = fields

    def add_method_or_error(value, replace=False):
        name = value.__name__
        if name in retval_dict and not replace:
            raise TypeError(
                f"can't generate {name} method: attribute already exists")
        value.__qualname__ = f"{cls.__qualname__}.{value.__name__}"
        retval_dict[name] = value

    if frozen:
        def __setattr__(self, name: str, value):
            if getattr(self, "__plain_data_init_done", False):
                raise FrozenPlainDataError(f"cannot assign to field {name!r}")
            elif name not in slots and not name.startswith("_"):
                raise AttributeError(
                    f"cannot assign to unknown field {name!r}")
            object.__setattr__(self, name, value)

        add_method_or_error(__setattr__)

        def __delattr__(self, name):
            if getattr(self, "__plain_data_init_done", False):
                raise FrozenPlainDataError(f"cannot delete field {name!r}")
            object.__delattr__(self, name)

        add_method_or_error(__delattr__)

        old_init = cls.__init__

        def __init__(self, *args, **kwargs):
            if hasattr(self, "__plain_data_init_done"):
                # we're already in an __init__ call (probably a
                # superclass's __init__), don't set
                # __plain_data_init_done too early
                return old_init(self, *args, **kwargs)
            object.__setattr__(self, "__plain_data_init_done", False)
            try:
                return old_init(self, *args, **kwargs)
            finally:
                object.__setattr__(self, "__plain_data_init_done", True)

        add_method_or_error(__init__, replace=True)
    else:
        old_init = None

    # set __slots__ to have everything we need in the preferred order
    retval_dict["__slots__"] = tuple(slots.keys())

    def __getstate__(self):
        # pickling support
        return [getattr(self, name) for name in fields]

    add_method_or_error(__getstate__)

    def __setstate__(self, state):
        # pickling support
        for name, value in zip(fields, state):
            # bypass frozen setattr
            object.__setattr__(self, name, value)

    add_method_or_error(__setstate__)

    # get source code that gets a tuple of all fields
    def fields_tuple(var):
        # type: (str) -> str
        l = []
        for name in fields:
            l.append(f"{var}.{name}, ")
        return "(" + "".join(l) + ")"

    if eq:
        exec(f"""
def __eq__(self, other):
    if other.__class__ is not self.__class__:
        return NotImplemented
    return {fields_tuple('self')} == {fields_tuple('other')}

add_method_or_error(__eq__)
""")

    if unsafe_hash:
        exec(f"""
def __hash__(self):
    return hash({fields_tuple('self')})

add_method_or_error(__hash__)
""")

    if order:
        exec(f"""
def __lt__(self, other):
    if other.__class__ is not self.__class__:
        return NotImplemented
    return {fields_tuple('self')} < {fields_tuple('other')}

add_method_or_error(__lt__)

def __le__(self, other):
    if other.__class__ is not self.__class__:
        return NotImplemented
    return {fields_tuple('self')} <= {fields_tuple('other')}

add_method_or_error(__le__)

def __gt__(self, other):
    if other.__class__ is not self.__class__:
        return NotImplemented
    return {fields_tuple('self')} > {fields_tuple('other')}

add_method_or_error(__gt__)

def __ge__(self, other):
    if other.__class__ is not self.__class__:
        return NotImplemented
    return {fields_tuple('self')} >= {fields_tuple('other')}

add_method_or_error(__ge__)
""")

    if repr_:
        def __repr__(self):
            parts = []
            for name in fields:
                parts.append(f"{name}={getattr(self, name, __NOT_SET)!r}")
            return f"{self.__class__.__qualname__}({', '.join(parts)})"

        add_method_or_error(__repr__)

    # construct class
    retval = type(cls)(cls.__name__, cls.__bases__, retval_dict)

    # add __qualname__
    retval.__qualname__ = cls.__qualname__

    def fix_super_and_class(value):
        # fixup super() and __class__
        # derived from: https://stackoverflow.com/a/71666065/2597900
        try:
            closure = value.__closure__
            if isinstance(closure, tuple):
                if closure[0].cell_contents is cls:
                    closure[0].cell_contents = retval
        except (AttributeError, IndexError):
            pass

    for value in retval.__dict__.values():
        fix_super_and_class(value)

    if old_init is not None:
        fix_super_and_class(old_init)

    return retval


def plain_data(*, eq=True, unsafe_hash=False, order=False, repr=True,
               frozen=False):
    # defaults match dataclass, with the exception of `init`
    """ Decorator for adding equality comparison, ordered comparison,
    `repr` support, `hash` support, and frozen type (read-only fields)
    support to classes that are just plain data.

    This is kinda like dataclasses, but uses `__slots__` instead of type
    annotations, as well as requiring you to write your own `__init__`
    """
    def decorator(cls):
        return _decorator(cls, eq=eq, unsafe_hash=unsafe_hash, order=order,
                          repr_=repr, frozen=frozen)
    return decorator


def fields(pd):
    """ get the tuple of field names of the passed-in
    `@plain_data()`-decorated class.

    This is similar to `dataclasses.fields`, except this returns a
    different type.

    Returns: tuple[str, ...]

    e.g.:
    ```
    @plain_data()
    class MyBaseClass:
        __slots__ = "a_field", "field2"
        def __init__(self, a_field, field2):
            self.a_field = a_field
            self.field2 = field2

    assert fields(MyBaseClass) == ("a_field", "field2")
    assert fields(MyBaseClass(1, 2)) == ("a_field", "field2")

    @plain_data()
    class MyClass(MyBaseClass):
        __slots__ = "child_field",
        def __init__(self, a_field, field2, child_field):
            super().__init__(a_field=a_field, field2=field2)
            self.child_field = child_field

    assert fields(MyClass) == ("a_field", "field2", "child_field")
    assert fields(MyClass(1, 2, 3)) == ("a_field", "field2", "child_field")
    ```
    """
    retval = getattr(pd, "__plain_data_fields", None)
    if not isinstance(retval, tuple):
        raise TypeError("the passed-in object must be a class or an instance"
                        " of a class decorated with @plain_data()")
    return retval


__NOT_SPECIFIED = object()


def replace(pd, **changes):
    """ Return a new instance of the passed-in `@plain_data()`-decorated
    object, but with the specified fields replaced with new values.
    This is quite useful with frozen `@plain_data()` classes.

    e.g.:
    ```
    @plain_data(frozen=True)
    class MyClass:
        __slots__ = "a", "b", "c"
        def __init__(self, a, b, *, c):
            self.a = a
            self.b = b
            self.c = c

    v1 = MyClass(1, 2, c=3)
    v2 = replace(v1, b=4)
    assert v2 == MyClass(a=1, b=4, c=3)
    assert v2 is not v1
    ```
    """
    kwargs = {}
    ty = type(pd)
    # call fields on ty rather than pd to ensure we're not called with a
    # class rather than an instance.
    for name in fields(ty):
        value = changes.pop(name, __NOT_SPECIFIED)
        if value is __NOT_SPECIFIED:
            kwargs[name] = getattr(pd, name)
        else:
            kwargs[name] = value
    if len(changes) != 0:
        raise TypeError(f"can't set unknown field {changes.popitem()[0]!r}")
    return ty(**kwargs)
