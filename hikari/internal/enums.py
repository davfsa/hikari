# Copyright (c) 2020 Nekokatt
# Copyright (c) 2021-present davfsa
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""Implementation of parts of Python's [`enum`][] protocol to be more performant."""

from __future__ import annotations

__all__: typing.Sequence[str] = ("Flag", "IntEnum", "StrEnum")

import enum
import typing

from hikari.internal import typing_extensions

if typing.TYPE_CHECKING:
    from typing_extensions import Self


@enum.unique
class StrEnum(enum.StrEnum):
    """Extension of [`enum.StrEnum`][] to suite hikari's needs.

    It implements a `_missing_` classmethod to handle deserializing
    unknown members.
    """

    __slots__: typing.Sequence[str] = ()

    @classmethod
    def _missing_(cls: type[Self], value: str) -> Self:
        pseudo_member = str.__new__(cls, value)
        pseudo_member._name_ = "UNKNOWN"
        pseudo_member._value_ = value
        return pseudo_member


@enum.unique
class IntEnum(enum.IntEnum):
    """Extension of [`enum.IntEnum`][] to suite hikari's needs.

    It implements a `_missing_` classmethod to handle deserializing
    unknown members.
    """

    __slots__: typing.Sequence[str] = ()

    @classmethod
    @typing_extensions.override
    def _missing_(cls: type[Self], value: object) -> Self:
        assert isinstance(value, int)
        pseudo_member = int.__new__(cls, value)
        pseudo_member._name_ = "UNKNOWN"
        pseudo_member._value_ = value
        return pseudo_member


@enum.unique
class Flag(enum.IntFlag):
    """Extension [`enum.Flag`][] implementation.

    In simple terms, a flag is a set of wrapped constant [`int`][]
    values that can be combined in any combination to make a special value.
    This is a more efficient way of combining things like permissions together
    into a single integral value, and works by setting the individual `1` and `0`
    on the binary representation of the integer.

    This implementation has extra features, in that it will actively behave
    like a [`set`][] as well.

    !!! warning
        It is important to keep in mind that some semantics such as subtype
        checking and instance checking may differ. It is recommended to compare
        these values using the `==` operator rather than the `is` operator for
        safety reasons.

        Especially where pseudo-members created from combinations are cached,
        results of using of `is` may not be deterministic. This is a side
        effect of some internal performance improvements.

        Failing to observe this __will__ result in unexpected behaviour
        occurring in your application!

        Also important to note is that despite wrapping [`int`][] values,
        conceptually this does not behave as if it were a subclass of [`int`][].

    Operators on each flag member
    -----------------------------
    * `e1 & e2` :
        Bitwise `AND` operation. Will return a member that contains all flags
        that are common between both operands on the values. This also works with
        one of the operands being an [`int`][]eger. You may instead use
        the `intersection` method.
    * `e1 | e2` :
        Bitwise `OR` operation. Will return a member that contains all flags
        that appear on at least one of the operands. This also works with
        one of the operands being an [`int`][]eger. You may instead use
        the `union` method.
    * `e1 ^ e2` :
        Bitwise `XOR` operation. Will return a member that contains all flags
        that only appear on at least one and at most one of the operands.
        This also works with one of the operands being an [`int`][].
        You may instead use the `symmetric_difference` method.
    * `~e` :
        Return the inverse of this value. This is equivalent to disabling all
        flags that are set on this value and enabling all flags that are
        not set on this value. Note that this will behave slightly differently
        to inverting a pure int value. You may instead use the `invert` method.
    * `e1 - e2` :
        Bitwise set difference operation. Returns all flags set on `e1` that are
        not set on `e2` as well. You may instead use the `difference`
        method.
    * `bool(e)` : [`bool`][]
        Return [`True`][] if `e` has a non-zero value, otherwise
        [`False`][].
    * `E.A in e`: [`bool`][]
        [`True`][] if `E.A` is in `e`. This is functionally equivalent
        to `E.A & e == E.A`.
    * `iter(e)` :
        Explode the value into a iterator of each __documented__ flag that can
        be combined to make up the value `e`. Returns an iterator across all
        well-defined flags that make up this value. This will only include the
        flags explicitly defined on this `Flag` type and that are individual
        powers of two (this means if converted to twos-compliment binary,
        exactly one bit must be a `1`). In simple terms, this means that you
        should not expect combination flags to be returned.
    * `e1 == e2` : [`bool`][]
        Compare equality.
    * `e1 != e2` : [`bool`][]
        Compare inequality.
    * `e1 < e2` : [`bool`][]
        Compare by ordering.
    * `int(e)` : [`int`][]
        Get the integer value of this flag
    * `repr(e)` : [`str`][]
        Get the machine readable representation of the flag member `e`.
    * `str(e)` : [`str`][]
        Get the [`str`][] name of the flag member `e`.

    Special members on each flag member
    -----------------------------------
    * `e.all(E.A, E.B, E.C, ...)` : [`bool`][]
        Returns [`True`][] if __all__ of `E.A`, `E.B`, `E.C`, et cetera
        make up the value of `e`.
    * `e.any(E.A, E.B, E.C, ...)` : [`bool`][]
        Returns [`True`][] if __any__ of `E.A`, `E.B`, `E.C`, et cetera
        make up the value of `e`.
    * `e.none(E.A, E.B, E.C, ...)` : [`bool`][]
        Returns [`True`][] if __none__ of `E.A`, `E.B`, `E.C`, et cetera
        make up the value of `e`.
    * `e.split()` : [`typing.Sequence`][]
        Explode the value into a sequence of each __documented__ flag that can
        be combined to make up the value `e`. Returns a sorted sequence of each
        power-of-two flag that makes up the value `e`. This is equivalent to
        `list(iter(e))`.

    All other methods and operators on `Flag` members are inherited from the
    member's __value__.
    """

    _name_: str
    _value_: int

    def all(self, *flags: int) -> bool:
        """Check if all of the given flags are part of this value.

        Returns
        -------
        bool
            [`True`][] if any of the given flags are part of this value.
            Otherwise, return [`False`][].
        """
        for flag in flags:
            if (flag & self) != flag:
                return False

        return True

    def any(self, *flags: int) -> bool:
        """Check if any of the given flags are part of this value.

        Returns
        -------
        bool
            [`True`][] if any of the given flags are part of this value.
            Otherwise, return [`False`][].
        """
        for flag in flags:
            if (flag & self) == flag:
                return True

        return False

    def difference(self, other: int) -> Self:
        """Perform a set difference with the other set.

        This will return all flags in this set that are not in the other value.

        Equivalent to using the subtraction `-` operator.
        """
        return self.__class__(self._value_ & ~int(other))

    def intersection(self, other: int) -> Self:
        """Return a combination of flags that are set for both given values.

        Equivalent to using the "AND" `&` operator.
        """
        return self.__class__(self._value_ & int(other))

    def invert(self) -> Self:
        """Return a set of all flags not in the current set."""
        return self.__class__(~self._value_)

    def is_disjoint(self, other: int) -> bool:
        """Return whether two sets have a intersection or not.

        If the two sets have an intersection, then this returns
        [`False`][]. If no common flag values exist between them, then
        this returns [`True`][].
        """
        return not (self & other)

    def is_subset(self, other: int) -> bool:
        """Return whether another set contains this set or not.

        Equivalent to using the "in" operator.
        """
        return (self & other) == other

    def is_superset(self, other: int) -> bool:
        """Return whether this set contains another set or not."""
        return (self & other) == self

    def none(self, *flags: int) -> bool:
        """Check if none of the given flags are part of this value.

        !!! note
            This is essentially the opposite of [`hikari.internal.enums.Flag.any`][].

        Returns
        -------
        bool
            [`True`][] if none of the given flags are part of this value.
            Otherwise, return [`False`][].
        """
        return not self.any(*flags)

    def split(self) -> typing.Sequence[Self]:
        """Return a list of all defined atomic values for this flag.

        Any unrecognised bits will be omitted for brevity.

        The result will be a name-sorted [`typing.Sequence`][] of each member
        """
        return sorted(
            (member for member in self if member._value_ & self),
            # Assumption: powers of 2 already have a cached value.
            key=lambda m: m._name_,
        )

    def symmetric_difference(self, other: int) -> Self:
        """Return a set with the symmetric differences of two flag sets.

        Equivalent to using the "XOR" `^` operator.

        For `a ^ b`, this can be considered the same as `(a - b) | (b - a)`.
        """
        return self.__class__(self._value_ ^ int(other))

    def union(self, other: int) -> Self:
        """Return a combination of all flags in this set and the other set.

        Equivalent to using the "OR" `~` operator.
        """
        return self.__class__(self._value_ | int(other))

    # Exists since Python's `set` type is inconsistent with naming, so this
    # will prevent tripping people up unnecessarily because we do not
    # name inconsistently.
    isdisjoint = is_disjoint
    issubset = is_subset
    issuperset = is_superset
    # This one isn't in Python's set, but the inconsistency is triggering my OCD
    # so this is being defined anyway.
    symmetricdifference = symmetric_difference

    @typing_extensions.override
    def __rsub__(self, other: int) -> Self:
        # This logic has to be reversed to be correct, since order matters for
        # a subtraction operator. This also ensures `int - _T -> _T` is a valid
        # case for us.
        return self.__class__(self.__class__(other) - self)

    @typing_extensions.override
    def __str__(self) -> str:
        return self._name_

    __contains__ = is_subset
    __rand__ = __and__ = intersection
    __ror__ = __or__ = union
    __sub__ = difference
    __rxor__ = __xor__ = symmetric_difference
    __invert__ = invert
