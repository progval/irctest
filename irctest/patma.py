"""Pattern-matching utilities"""

import dataclasses
import itertools
import re
from typing import Dict, List, Optional, Union


class Operator:
    """Used as a wildcards and operators when matching message arguments
    (see assertMessageMatch and match_list)"""

    def __init__(self) -> None:
        pass


class _AnyStr(Operator):
    """Wildcard matching any string"""

    def __repr__(self) -> str:
        return "ANYSTR"


class _AnyOptStr(Operator):
    """Wildcard matching any string as well as None"""

    def __repr__(self) -> str:
        return "ANYOPTSTR"


@dataclasses.dataclass(frozen=True)
class OptStrRe(Operator):
    regexp: str

    def __repr__(self) -> str:
        return f"OptStrRe(r'{self.regexp}')"


@dataclasses.dataclass(frozen=True)
class StrRe(Operator):
    regexp: str

    def __repr__(self) -> str:
        return f"StrRe(r'{self.regexp}')"


@dataclasses.dataclass(frozen=True)
class NotStrRe(Operator):
    regexp: str

    def __repr__(self) -> str:
        return f"NotStrRe(r'{self.regexp}')"


@dataclasses.dataclass(frozen=True)
class InsensitiveStr(Operator):
    string: str

    def __repr__(self) -> str:
        return f"InsensitiveStr({self.string!r})"


@dataclasses.dataclass(frozen=True)
class RemainingKeys(Operator):
    """Used in a dict pattern to match all remaining keys.
    May only be present once."""

    key: Operator

    def __repr__(self) -> str:
        return f"RemainingKeys({self.key!r})"


ANYSTR = _AnyStr()
"""Singleton, spares two characters"""

ANYOPTSTR = _AnyOptStr()
"""Singleton, spares two characters"""

ANYDICT = {RemainingKeys(ANYSTR): ANYOPTSTR}
"""Matches any dictionary; useful to compare tags dict, eg.
`match_dict(got_tags, {"label": "foo", **ANYDICT})`"""


@dataclasses.dataclass(frozen=True)
class ListRemainder:
    item: Operator
    min_length: int = 0

    def __repr__(self) -> str:
        if self.min_length:
            return f"ListRemainder({self.item!r}, min_length={self.min_length})"
        elif self.item is ANYSTR:
            return "*ANYLIST"
        else:
            return f"ListRemainder({self.item!r})"


ANYLIST = [ListRemainder(ANYSTR)]
"""Matches any list remainder"""


def match_string(got: Optional[str], expected: Union[str, Operator, None]) -> bool:
    if isinstance(expected, _AnyOptStr):
        return True
    elif isinstance(expected, _AnyStr) and got is not None:
        return True
    elif isinstance(expected, StrRe):
        if got is None or not re.match(expected.regexp + "$", got):
            return False
    elif isinstance(expected, OptStrRe):
        if got is None:
            return True
        if not re.match(expected.regexp + "$", got):
            return False
    elif isinstance(expected, NotStrRe):
        if got is None or re.match(expected.regexp + "$", got):
            return False
    elif isinstance(expected, InsensitiveStr):
        if got is None or got.lower() != expected.string.lower():
            return False
    elif isinstance(expected, Operator):
        raise NotImplementedError(f"Unsupported operator: {expected}")
    elif got != expected:
        return False

    return True


def match_list(
    got: List[Optional[str]], expected: List[Union[str, None, Operator]]
) -> bool:
    """Returns True iff the list are equal.

    The ANYSTR operator can be used on the 'expected' side as a wildcard,
    matching any *single* value; and StrRe("<regexp>") can be used to match regular
    expressions"""
    if expected and isinstance(expected[-1], ListRemainder):
        # Expand the 'expected' list to have as many items as the 'got' list
        expected = list(expected)  # copy
        remainder = expected.pop()
        nb_remaining_items = len(got) - len(expected)
        expected += [remainder.item] * max(nb_remaining_items, remainder.min_length)

    nb_optionals = 0
    for expected_value in expected:
        if isinstance(expected_value, (_AnyOptStr, OptStrRe)):
            nb_optionals += 1
        else:
            if nb_optionals > 0:
                raise NotImplementedError("Optional values in non-final position")

    if not (len(expected) - nb_optionals <= len(got) <= len(expected)):
        return False
    return all(
        match_string(got_value, expected_value)
        for (got_value, expected_value) in itertools.zip_longest(got, expected)
    )


def match_dict(
    got: Dict[str, Optional[str]],
    expected: Dict[Union[str, Operator], Union[str, Operator, None]],
) -> bool:
    """Returns True iff the list are equal.

    The ANYSTR operator can be used on the 'expected' side as a wildcard,
    matching any *single* value; and StrRe("<regexp>") can be used to match regular
    expressions
    Additionally, the Keys() operator can be used to match remaining keys, and
    ANYDICT to match any remaining dict"""
    got = dict(got)  # shallow copy, as we will remove keys

    # Set to not-None if we find a Keys() operator in the dict keys
    remaining_keys_wildcard = None

    for expected_key, expected_value in expected.items():
        if isinstance(expected_key, RemainingKeys):
            remaining_keys_wildcard = (expected_key.key, expected_value)
        else:
            for key in got:
                if match_string(key, expected_key) and match_string(
                    got[key], expected_value
                ):
                    got.pop(key)
                    break
            else:
                # Found no (key, value) pair matching the request
                return False

    if remaining_keys_wildcard:
        (expected_key, expected_value) = remaining_keys_wildcard
        for key, value in got.items():
            if not match_string(key, expected_key):
                return False
            if not match_string(value, expected_value):
                return False

        return True
    else:
        # There should be nothing left unmatched in the dict
        return got == {}
