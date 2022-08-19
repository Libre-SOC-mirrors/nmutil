# SPDX-License-Identifier: LGPL-3-or-later
# Copyright 2022 Jacob Lifshay programmerjake@gmail.com

# Funded by NLnet Assure Programme 2021-02-052, https://nlnet.nl/assure part
# of Horizon 2020 EU Programme 957073.

from collections import defaultdict
import operator
from nmigen.hdl.ast import Value, Const
from nmutil.plain_data import plain_data


@plain_data(order=True, unsafe_hash=True, frozen=True)
class Op:
    """An associative operation in a prefix-sum.
    The operation is `items[self.out] = fn(items[self.lhs], items[self.rhs])`.
    The operation is not assumed to be commutative.
    """
    __slots__ = "out", "lhs", "rhs", "row"

    def __init__(self, out, lhs, rhs, row):
        self.out = out
        "index of the item to output to"

        self.lhs = lhs
        "index of the item the left-hand-side input comes from"

        self.rhs = rhs
        "index of the item the right-hand-side input comes from"

        self.row = row
        "row in the prefix-sum diagram"


def prefix_sum_ops(item_count, *, work_efficient=False):
    """Get the associative operations needed to compute a parallel prefix-sum
    of `item_count` items.

    The operations aren't assumed to be commutative.

    This has a depth of `O(log(N))` and an operation count of `O(N)` if
    `work_efficient` is true, otherwise `O(N*log(N))`.

    The algorithms used are derived from:
    https://en.wikipedia.org/wiki/Prefix_sum#Algorithm_1:_Shorter_span,_more_parallel
    https://en.wikipedia.org/wiki/Prefix_sum#Algorithm_2:_Work-efficient

    Parameters:
    item_count: int
        number of input items.
    work_efficient: bool
        True if the algorithm used should be work-efficient -- has a larger
        depth (about twice as large) but does only `O(N)` operations total
        instead of `O(N*log(N))`.
    Returns: Iterable[Op]
        output associative operations.
    """
    assert isinstance(item_count, int)
    # compute the partial sums using a set of binary trees
    # this is the first half of the work-efficient algorithm and the whole of
    # the non-work-efficient algorithm.
    dist = 1
    row = 0
    while dist < item_count:
        start = dist * 2 - 1 if work_efficient else dist
        step = dist * 2 if work_efficient else 1
        for i in reversed(range(start, item_count, step)):
            yield Op(out=i, lhs=i - dist, rhs=i, row=row)
        dist <<= 1
        row += 1
    if work_efficient:
        # express all output items in terms of the computed partial sums.
        dist >>= 1
        while dist >= 1:
            for i in reversed(range(dist * 3 - 1, item_count, dist * 2)):
                yield Op(out=i, lhs=i - dist, rhs=i, row=row)
            row += 1
            dist >>= 1


def prefix_sum(items, fn=operator.add, *, work_efficient=False):
    """Compute the parallel prefix-sum of `items`, using associative operator
    `fn` instead of addition.

    This has a depth of `O(log(N))` and an operation count of `O(N)` if
    `work_efficient` is true, otherwise `O(N*log(N))`.

    The algorithms used are derived from:
    https://en.wikipedia.org/wiki/Prefix_sum#Algorithm_1:_Shorter_span,_more_parallel
    https://en.wikipedia.org/wiki/Prefix_sum#Algorithm_2:_Work-efficient

    Parameters:
    items: Iterable[_T]
        input items.
    fn: Callable[[_T, _T], _T]
        Operation to use for the prefix-sum algorithm instead of addition.
        Assumed to be associative not necessarily commutative.
    work_efficient: bool
        True if the algorithm used should be work-efficient -- has a larger
        depth (about twice as large) but does only `O(N)` operations total
        instead of `O(N*log(N))`.
    Returns: list[_T]
        output items.
    """
    items = list(items)
    for op in prefix_sum_ops(len(items), work_efficient=work_efficient):
        items[op.out] = fn(items[op.lhs], items[op.rhs])
    return items


@plain_data()
class _Cell:
    __slots__ = "slant", "plus", "tee"

    def __init__(self, slant, plus, tee):
        self.slant = slant
        self.plus = plus
        self.tee = tee


def render_prefix_sum_diagram(item_count, *, work_efficient=False,
                              sp=" ", vbar="|", plus="⊕",
                              slant="\\", connect="●", no_connect="X",
                              padding=1,
                              ):
    """renders a prefix-sum diagram, matches `prefix_sum_ops`.

    Parameters:
    item_count: int
        number of input items.
    work_efficient: bool
        True if the algorithm used should be work-efficient -- has a larger
        depth (about twice as large) but does only `O(N)` operations total
        instead of `O(N*log(N))`.
    sp: str
        character used for blank space
    vbar: str
        character used for a vertical bar
    plus: str
        character used for the addition operation
    slant: str
        character used to draw a line from the top left to the bottom right
    connect: str
        character used to draw a connection between a vertical line and a line
        going from the center of this character to the bottom right
    no_connect: str
        character used to draw two lines crossing but not connecting, the lines
        are vertical and diagonal from top left to the bottom right
    padding: int
        amount of padding characters in the output cells.
    Returns: str
        rendered diagram
    """
    ops_by_row = defaultdict(set)
    for op in prefix_sum_ops(item_count, work_efficient=work_efficient):
        assert op.out == op.rhs, f"can't draw op: {op}"
        assert op not in ops_by_row[op.row], f"duplicate op: {op}"
        ops_by_row[op.row].add(op)

    def blank_row():
        return [_Cell(slant=False, plus=False, tee=False)
                for _ in range(item_count)]

    cells = [blank_row()]

    for row in sorted(ops_by_row.keys()):
        ops = ops_by_row[row]
        max_distance = max(op.rhs - op.lhs for op in ops)
        cells.extend(blank_row() for _ in range(max_distance))
        for op in ops:
            assert op.lhs < op.rhs and op.out == op.rhs, f"can't draw op: {op}"
            y = len(cells) - 1
            x = op.out
            cells[y][x].plus = True
            x -= 1
            y -= 1
            while op.lhs < x:
                cells[y][x].slant = True
                x -= 1
                y -= 1
            cells[y][x].tee = True

    lines = []
    for cells_row in cells:
        row_text = [[] for y in range(2 * padding + 1)]
        for cell in cells_row:
            # top padding
            for y in range(padding):
                # top left padding
                for x in range(padding):
                    is_slant = x == y and (cell.plus or cell.slant)
                    row_text[y].append(slant if is_slant else sp)
                # top vertical bar
                row_text[y].append(vbar)
                # top right padding
                for x in range(padding):
                    row_text[y].append(sp)
            # center left padding
            for x in range(padding):
                row_text[padding].append(sp)
            # center
            center = vbar
            if cell.plus:
                center = plus
            elif cell.tee:
                center = connect
            elif cell.slant:
                center = no_connect
            row_text[padding].append(center)
            # center right padding
            for x in range(padding):
                row_text[padding].append(sp)
            # bottom padding
            for y in range(padding + 1, 2 * padding + 1):
                # bottom left padding
                for x in range(padding):
                    row_text[y].append(sp)
                # bottom vertical bar
                row_text[y].append(vbar)
                # bottom right padding
                for x in range(padding + 1, 2 * padding + 1):
                    is_slant = x == y and (cell.tee or cell.slant)
                    row_text[y].append(slant if is_slant else sp)
        for line in row_text:
            lines.append("".join(line))

    return "\n".join(map(str.rstrip, lines))


def partial_prefix_sum_ops(needed_outputs, *, work_efficient=False):
    """ Get the associative operations needed to compute a parallel prefix-sum
    of `len(needed_outputs)` items.

    The operations aren't assumed to be commutative.

    This has a depth of `O(log(N))` and an operation count of `O(N)` if
    `work_efficient` is true, otherwise `O(N*log(N))`.

    The algorithms used are derived from:
    https://en.wikipedia.org/wiki/Prefix_sum#Algorithm_1:_Shorter_span,_more_parallel
    https://en.wikipedia.org/wiki/Prefix_sum#Algorithm_2:_Work-efficient

    Parameters:
    needed_outputs: Iterable[bool]
        The length is the number of input/output items.
        Each item is True if that corresponding output is needed.
        Unneeded outputs have unspecified value.
    work_efficient: bool
        True if the algorithm used should be work-efficient -- has a larger
        depth (about twice as large) but does only `O(N)` operations total
        instead of `O(N*log(N))`.
    Returns: Iterable[Op]
        output associative operations.
    """

    # needed_outputs is an iterable, we need to construct a new list so we
    # don't modify the passed-in value
    items_live_flags = [bool(i) for i in needed_outputs]
    ops = list(prefix_sum_ops(item_count=len(items_live_flags),
                              work_efficient=work_efficient))
    ops_live_flags = [False] * len(ops)
    for i in reversed(range(len(ops))):
        op = ops[i]
        out_live = items_live_flags[op.out]
        items_live_flags[op.out] = False
        items_live_flags[op.lhs] |= out_live
        items_live_flags[op.rhs] |= out_live
        ops_live_flags[i] = out_live
    for op, live_flag in zip(ops, ops_live_flags):
        if live_flag:
            yield op


def tree_reduction_ops(item_count):
    assert item_count >= 1
    needed_outputs = (i == item_count - 1 for i in range(item_count))
    return partial_prefix_sum_ops(needed_outputs)


def tree_reduction(items, fn=operator.add):
    items = list(items)
    for op in tree_reduction_ops(len(items)):
        items[op.out] = fn(items[op.lhs], items[op.rhs])
    return items[-1]


if __name__ == "__main__":
    print("the non-work-efficient algorithm, matches the diagram in wikipedia:"
          "\n"
          "https://commons.wikimedia.org/wiki/File:Hillis-Steele_Prefix_Sum.svg"
          "\n\n")
    print(render_prefix_sum_diagram(16, work_efficient=False))
    print()
    print()
    print("the work-efficient algorithm, matches the diagram in wikipedia:")
    print("https://en.wikipedia.org/wiki/File:Prefix_sum_16.svg")
    print()
    print(render_prefix_sum_diagram(16, work_efficient=True))
    print()
    print()
