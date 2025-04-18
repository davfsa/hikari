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

__all__: typing.Sequence[str] = ("Flag", "Enum")

import enum
import typing

from hikari.internal import typing_extensions

if typing.TYPE_CHECKING:
    from typing_extensions import Self

_MAX_CACHED_MEMBERS: typing.Final[int] = 1 << 12

Enum = Flag = NotImplemented

class _EnumMeta(enum.EnumMeta):
    # TODO: Remove in the future when we use msgspec structs
    #       or we find a way to make sure that (typing wise)
    #       that the correct type will be passed to enums and flags
    def __call__(cls: type[Self], value: object) -> Self:
        return cls.__new__(cls, cls._member_type_(value))

    def __new__(
        mcls: type[Self],
        cls_name: str,
        bases: tuple[type[typing.Any], ...],
        namespace: dict[str, typing.Any],
    ) -> Self:
        # The first two that will be created will be the base classes.
        if Enum is NotImplemented or Flag is NotImplemented:
            # We are creating the base classes, so continue normally
            return super().__new__(mcls, cls_name, bases, namespace)

        # Ensure proper usage by passing 2 bases
        if Flag in bases:
            if len(bases) != 1:
                msg = "Expected exactly one base class for a flag"
                raise TypeError(msg)
        else:
            if len(bases) != 2:
                msg = "Expected exactly two base classes for an enum"
                raise TypeError(msg)

        obj = super().__new__(mcls, cls_name, bases, namespace)

        # Ensure there are no unhashable values in the enum.
        if len(obj._unhashable_values_) != 0:
            msg = f"Cannot have unhashable values in this enum type ({', '.join(obj._unhashable_values_)})"
            raise TypeError(msg)

        # CPython will place a str that we dont want it if its not present in the namespace, but
        # we want to replace it with str's __str__ if we do not define one ourselves.
        if issubclass(obj, str) and "__str__" not in namespace:
            obj.__str__ = str.__str__

        return obj

    def __iter__(cls) -> typing.Iterator[Enum]:
        yield from cls._member_map_.values()

    def __repr__(cls) -> str:
        return f"<enum {cls.__name__}>"

    __str__ = __repr__

@enum.unique
class Enum(enum.Enum, metaclass=_EnumMeta):
    """Extension of [`enum.Enum`][] to suite hikari's needs."""

    @classmethod
    @typing_extensions.override
    def _missing_(cls: type[Self], value: object) -> Self:
        pseudo_member = cls._member_type_.__new__(cls, value)
        pseudo_member._name_ = "UNKNOWN"
        pseudo_member._value_ = value
        return pseudo_member

def _name_resolver(members: dict[int, Flag], value: int) -> typing.Generator[str, typing.Any, None]:
    bit = 1
    has_yielded = False
    remaining = value
    while bit <= value:
        # Use ._value_ to prevent overhead of making new members each time.
        # Also let's my testing logic for the cache size be more accurate.
        member = members.get(bit)
        if member and member._value_ & remaining == member._value_:
            remaining ^= member._value_
            yield member.name
            has_yielded = True
        bit <<= 1

    if not has_yielded:
        yield f"UNKNOWN 0x{value:x}"
    elif remaining:
        yield hex(remaining)

class _FlagMeta(_EnumMeta):
    # FIXME: This is mostly a syntactic sugar to default Flag() to Flag.NONE
    #        Should we keep it?
    def __call__(cls: type[Self], value: int = 0) -> Self:
        return super().__call__(value)

    def __new__(
        mcls: type[Self],
        cls_name: str,
        bases: tuple[type[typing.Any], ...],
        namespace: dict[str, typing.Any],
    ) -> Self:
        # To use for caching composite members
        #
        # This is kinda hacky, but its the only way to bypass the
        # __setitem__ that the enum implementation binds to
        dict.__setitem__(namespace, "_temp_members_", {})

        return super().__new__(mcls, cls_name, bases, namespace)


@enum.unique
class Flag(enum.IntFlag, metaclass=_FlagMeta):
    """Extension [`enum.Flag`][] implementation to suite hikari's needs.

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

    __slots__: typing.Sequence[str] = ()

    _name_: str | None
    _value_: int
    _all_bits_: int
    _value2member_map_: dict[int, Flag]
    _temp_members_: dict[int, Flag]

    @classmethod
    def _missing_(cls, value: int) -> Self:
        if value < 0:
            value = cls._all_bits_ - ~value

        try:
            return cls._temp_members_[value]

        except KeyError:
            pseudo_member = int.__new__(cls, value)
            pseudo_member._name_ = None
            pseudo_member._value_ = value

            if len(cls._temp_members_) >= _MAX_CACHED_MEMBERS:
                cls._temp_members_.popitem()

            cls._temp_members_[value] = pseudo_member
            return pseudo_member

    @property
    def name(self) -> str:
        """Return the name of the flag combination as a [`str`][]."""
        if self._name_ is None:
            self._name_ = "|".join(_name_resolver(self._value2member_map_, self._value_))
        return self._name_

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
        # Note: It is important to use `.name` here instead of `._name_`, as it might be None
        return self.name

    __contains__ = is_subset
    __rand__ = __and__ = intersection
    __ror__ = __or__ = union
    __sub__ = difference
    __rxor__ = __xor__ = symmetric_difference
    __invert__ = invert
