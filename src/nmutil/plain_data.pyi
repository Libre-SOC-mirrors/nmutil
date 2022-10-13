# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2022 Jacob Lifshay programmerjake@gmail.com

from typing import TypeVar, Type, Callable, Any

_T = TypeVar("_T")


class FrozenPlainDataError(AttributeError):
    pass


def plain_data(*, eq: bool = True, unsafe_hash: bool = False,
               order: bool = False, repr: bool = True,
               frozen: bool = False) -> Callable[[Type[_T]], Type[_T]]:
    ...


def fields(pd: Any) -> tuple[str, ...]:
    ...


def replace(pd: _T, **changes: Any) -> _T:
    ...
