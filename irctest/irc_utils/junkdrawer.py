import datetime
import secrets
import socket
from typing import List, Set, Tuple

from irctest.numerics import RPL_NAMREPLY

from .message_parser import Message

# thanks jess!
IRCV3_FORMAT_STRFTIME = "%Y-%m-%dT%H:%M:%S.%f%z"


def ircv3_timestamp_to_unixtime(timestamp: str) -> float:
    return datetime.datetime.strptime(timestamp, IRCV3_FORMAT_STRFTIME).timestamp()


def random_name(base: str) -> str:
    return base + "-" + secrets.token_hex(5)


def find_hostname_and_port() -> Tuple[str, int]:
    """Find available hostname/port to listen on."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(("", 0))
    (hostname, port) = s.getsockname()
    s.close()
    return (hostname, port)


def parse_rplnamreply(msgs: List[Message]) -> Set[str]:
    """Extract the set of names from RPL_NAMREPLY messages.

    Args:
        msgs: List of IRC messages to parse

    Returns:
        Set of names (nicknames with channel status prefixes like @, ~, %, +)
    """
    names = set()
    for msg in msgs:
        if msg.command != RPL_NAMREPLY:
            continue
        names.update(msg.params[3].split())
    return names
