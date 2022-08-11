# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2022 Jacob Lifshay programmerjake@gmail.com

class FrozenPlainDataError(AttributeError):
    pass


def _decorator(cls, *, eq, unsafe_hash, order, repr_, frozen):
    if not isinstance(cls, type):
        raise TypeError(
            "plain_data() can only be used as a class decorator")
    # slots is an ordered set by using dict keys.
    # always add __dict__ and __weakref__
    slots = {"__dict__": None, "__weakref__": None}
    fields = []
    any_parents_have_dict = False
    any_parents_have_weakref = False
    for cur_cls in reversed(cls.__mro__):
        if cur_cls is object:
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
            if field not in slots:
                fields.append(field)
            slots[field] = None
            if cur_cls is not cls:
                if field == "__dict__":
                    any_parents_have_dict = True
                elif field == "__weakref__":
                    any_parents_have_weakref = True

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

    def add_method_or_error(value, replace=False):
        name = value.__name__
        if name in retval_dict and not replace:
            raise TypeError(
                f"can't generate {name} method: attribute already exists")
        value.__qualname__ = f"{cls.__qualname__}.{value.__name__}"
        retval_dict[name] = value

    if frozen:
        slots["__plain_data_init_done"] = None

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

    # set __slots__ to have everything we need in the preferred order
    retval_dict["__slots__"] = tuple(slots.keys())

    def __dir__(self):
        # don't return fields un-copied so users can't mess with it
        return fields.copy()

    add_method_or_error(__dir__)

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

    # get a tuple of all fields
    def fields_tuple(self):
        return tuple(getattr(self, name) for name in fields)

    if eq:
        def __eq__(self, other):
            if other.__class__ is not self.__class__:
                return NotImplemented
            return fields_tuple(self) == fields_tuple(other)

        add_method_or_error(__eq__)

    if unsafe_hash:
        def __hash__(self):
            return hash(fields_tuple(self))

        add_method_or_error(__hash__)

    if order:
        def __lt__(self, other):
            if other.__class__ is not self.__class__:
                return NotImplemented
            return fields_tuple(self) < fields_tuple(other)

        add_method_or_error(__lt__)

        def __le__(self, other):
            if other.__class__ is not self.__class__:
                return NotImplemented
            return fields_tuple(self) <= fields_tuple(other)

        add_method_or_error(__le__)

        def __gt__(self, other):
            if other.__class__ is not self.__class__:
                return NotImplemented
            return fields_tuple(self) > fields_tuple(other)

        add_method_or_error(__gt__)

        def __ge__(self, other):
            if other.__class__ is not self.__class__:
                return NotImplemented
            return fields_tuple(self) >= fields_tuple(other)

        add_method_or_error(__ge__)

    if repr_:
        def __repr__(self):
            parts = []
            for name in fields:
                parts.append(f"{name}={getattr(self, name)!r}")
            return f"{self.__class__.__qualname__}({', '.join(parts)})"

        add_method_or_error(__repr__)

    # construct class
    retval = type(cls)(cls.__name__, cls.__bases__, retval_dict)

    # add __qualname__
    retval.__qualname__ = cls.__qualname__

    # fixup super() and __class__
    # derived from: https://stackoverflow.com/a/71666065/2597900
    for value in retval.__dict__.values():
        try:
            closure = value.__closure__
            if isinstance(closure, tuple):
                if closure[0].cell_contents is cls:
                    closure[0].cell_contents = retval
        except (AttributeError, IndexError):
            pass

    return retval


def plain_data(*, eq=True, unsafe_hash=False, order=True, repr=True,
               frozen=False):
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
