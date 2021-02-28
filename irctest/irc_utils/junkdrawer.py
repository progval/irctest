import datetime
import re
import secrets
from typing import Dict

# thanks jess!
IRCV3_FORMAT_STRFTIME = "%Y-%m-%dT%H:%M:%S.%f%z"


def ircv3_timestamp_to_unixtime(timestamp: str) -> float:
    return datetime.datetime.strptime(timestamp, IRCV3_FORMAT_STRFTIME).timestamp()


def random_name(base: str) -> str:
    return base + "-" + secrets.token_hex(8)


"""
Stolen from supybot:
"""


class MultipleReplacer:
    """Return a callable that replaces all dict keys by the associated
    value. More efficient than multiple .replace()."""

    # We use an object instead of a lambda function because it avoids the
    # need for using the staticmethod() on the lambda function if assigning
    # it to a class in Python 3.
    def __init__(self, dict_: Dict[str, str]):
        self._dict = dict_
        dict_ = dict([(re.escape(key), val) for key, val in dict_.items()])
        self._matcher = re.compile("|".join(dict_.keys()))

    def __call__(self, s: str) -> str:
        return self._matcher.sub(lambda m: self._dict[m.group(0)], s)


def normalizeWhitespace(s: str, removeNewline: bool = True) -> str:
    r"""Normalizes the whitespace in a string; \s+ becomes one space."""
    if not s:
        return str(s)  # not the same reference
    starts_with_space = s[0] in " \n\t\r"
    ends_with_space = s[-1] in " \n\t\r"
    if removeNewline:
        newline_re = re.compile("[\r\n]+")
        s = " ".join(filter(bool, newline_re.split(s)))
    s = " ".join(filter(bool, s.split("\t")))
    s = " ".join(filter(bool, s.split(" ")))
    if starts_with_space:
        s = " " + s
    if ends_with_space:
        s += " "
    return s
