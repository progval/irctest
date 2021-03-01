"""Pattern-matching utilities"""

import dataclasses
import re
from typing import Dict, List, Optional, Union


class Operator:
    """Used as a wildcards and operators when matching message arguments
    (see assertMessageMatch and match_list)"""

    def __init__(self) -> None:
        pass


class AnyStr(Operator):
    """Wildcard matching any string"""

    def __repr__(self) -> str:
        return "AnyStr"


class AnyOptStr(Operator):
    """Wildcard matching any string as well as None"""

    def __repr__(self) -> str:
        return "AnyOptStr"


@dataclasses.dataclass(frozen=True)
class StrRe(Operator):
    regexp: str

    def __repr__(self) -> str:
        return f"StrRe(r'{self.regexp}')"


@dataclasses.dataclass(frozen=True)
class RemainingKeys(Operator):
    """Used in a dict pattern to match all remaining keys.
    May only be present once."""

    key: Operator

    def __repr__(self) -> str:
        return f"Keys({self.key!r})"


ANYSTR = AnyStr()
"""Singleton, spares two characters"""

ANYDICT = {RemainingKeys(ANYSTR): AnyOptStr()}
"""Matches any dictionary; useful to compare tags dict, eg.
`match_dict(got_tags, {"label": "foo", **ANYDICT})`"""


def match_string(got: Optional[str], expected: Union[str, Operator, None]) -> bool:
    if isinstance(expected, AnyOptStr):
        return True
    elif isinstance(expected, AnyStr) and got is not None:
        return True
    elif isinstance(expected, StrRe):
        if got is None or not re.match(expected.regexp, got):
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
    if len(got) != len(expected):
        return False
    return all(
        match_string(got_value, expected_value)
        for (got_value, expected_value) in zip(got, expected)
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

    for (expected_key, expected_value) in expected.items():
        if isinstance(expected_key, RemainingKeys):
            remaining_keys_wildcard = (expected_key.key, expected_value)
        elif isinstance(expected_key, Operator):
            raise NotImplementedError(f"Unsupported operator: {expected_key}")
        else:
            if expected_key not in got:
                return False
            got_value = got.pop(expected_key)
            if not match_string(got_value, expected_value):
                return False

    if remaining_keys_wildcard:
        (expected_key, expected_value) = remaining_keys_wildcard
        for (key, value) in got.items():
            if not match_string(key, expected_key):
                return False
            if not match_string(value, expected_value):
                return False

        return True
    else:
        # There should be nothing left unmatched in the dict
        return got == {}
