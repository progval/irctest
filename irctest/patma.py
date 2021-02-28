"""Pattern-matching utilities"""

import dataclasses
import re
from typing import List, Union


class Operator:
    """Used as a wildcards and operators when matching message arguments
    (see assertMessageMatch and match_list)"""

    def __init__(self) -> None:
        pass


class AnyStr(Operator):
    """Wildcard matching any string"""

    def __repr__(self) -> str:
        return "AnyStr"


@dataclasses.dataclass
class StrRe(Operator):
    regexp: str

    def __repr__(self) -> str:
        return f"StrRe(r'{self.regexp}')"


ANYSTR = AnyStr()
"""Singleton, spares two characters"""


def match_list(got: List[str], expected: List[Union[str, Operator]]) -> bool:
    """Returns True iff the list are equal.
    The ellipsis (aka. "..." aka triple dots) can be used on the 'expected'
    side as a wildcard, matching any *single* value."""
    if len(got) != len(expected):
        return False
    for (got_value, expected_value) in zip(got, expected):
        if isinstance(expected_value, AnyStr):
            # wildcard
            continue
        elif isinstance(expected_value, StrRe):
            if not re.match(expected_value.regexp, got_value):
                return False
        else:
            if got_value != expected_value:
                return False
    return True
