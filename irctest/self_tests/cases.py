from typing import Dict, List, Tuple

import pytest

from irctest import cases
from irctest.irc_utils.message_parser import parse_message
from irctest.patma import (
    ANYDICT,
    ANYLIST,
    ANYSTR,
    AnyOptStr,
    ListRemainder,
    NotStrRe,
    RemainingKeys,
    StrRe,
)

# fmt: off
MESSAGE_SPECS: List[Tuple[Dict, List[str], List[str]]] = [
    (
        # the specification:
        dict(
            command="PRIVMSG",
            params=["#chan", "hello"],
        ),
        # matches:
        [
            "PRIVMSG #chan hello",
            "PRIVMSG #chan :hello",
            "@tag1=bar PRIVMSG #chan :hello",
            "@tag1=bar;tag2= PRIVMSG #chan :hello",
            ":foo!baz@qux PRIVMSG #chan hello",
            "@tag1=bar :foo!baz@qux PRIVMSG #chan :hello",
        ],
        # and does not match:
        [
            "PRIVMSG #chan hello2",
            "PRIVMSG #chan2 hello",
        ]
    ),
    (
        # the specification:
        dict(
            command="PRIVMSG",
            params=["#chan", StrRe("hello.*")],
        ),
        # matches:
        [
            "PRIVMSG #chan hello",
            "PRIVMSG #chan :hello",
            "PRIVMSG #chan hello2",
            "@tag1=bar PRIVMSG #chan :hello",
            "@tag1=bar;tag2= PRIVMSG #chan :hello",
            ":foo!baz@qux PRIVMSG #chan hello",
            "@tag1=bar :foo!baz@qux PRIVMSG #chan :hello",
        ],
        # and does not match:
        [
            "PRIVMSG #chan :hi",
            "PRIVMSG #chan2 hello",
        ]
    ),
    (
        # the specification:
        dict(
            nick="foo",
            command="PRIVMSG",
        ),
        # matches:
        [
            ":foo!baz@qux PRIVMSG #chan hello",
            "@tag1=bar :foo!baz@qux PRIVMSG #chan :hello",
        ],
        # and does not match:
        [
            "PRIVMSG #chan :hi",
            ":foo2!baz@qux PRIVMSG #chan hello",
            "@tag1=bar :foo2!baz@qux PRIVMSG #chan :hello",
        ]
    ),
    (
        # the specification:
        dict(
            tags={"tag1": "bar"},
            command="PRIVMSG",
            params=["#chan", "hello"],
        ),
        # matches:
        [
            "@tag1=bar PRIVMSG #chan :hello",
            "@tag1=bar :foo!baz@qux PRIVMSG #chan :hello",
        ],
        # and does not match:
        [
            "@tag1=bar;tag2= PRIVMSG #chan :hello",
            "@tag1=value1 PRIVMSG #chan :hello",
            "PRIVMSG #chan hello",
            ":foo!baz@qux PRIVMSG #chan hello",
        ]
    ),
    (
        # the specification:
        dict(
            tags={"tag1": ANYSTR},
            command="PRIVMSG",
            params=["#chan", ANYSTR],
        ),
        # matches:
        [
            "@tag1=bar PRIVMSG #chan :hello",
            "@tag1=value1 PRIVMSG #chan :hello",
            "@tag1=bar :foo!baz@qux PRIVMSG #chan :hello",
        ],
        # and does not match:
        [
            "@tag1=bar;tag2= PRIVMSG #chan :hello",
            "PRIVMSG #chan hello",
            ":foo!baz@qux PRIVMSG #chan hello",
        ]
    ),
    (
        # the specification:
        dict(
            tags={"tag1": "bar", **ANYDICT},
            command="PRIVMSG",
            params=["#chan", "hello"],
        ),
        # matches:
        [
            "@tag1=bar PRIVMSG #chan :hello",
            "@tag1=bar;tag2= PRIVMSG #chan :hello",
            "@tag1=bar :foo!baz@qux PRIVMSG #chan :hello",
        ],
        # and does not match:
        [
            "PRIVMG #chan :hello",
            "@tag1=value1 PRIVMSG #chan :hello",
            "PRIVMSG #chan hello2",
            "PRIVMSG #chan2 hello",
            ":foo!baz@qux PRIVMSG #chan hello",
        ]
    ),
    (
        # the specification:
        dict(
            tags={"tag1": "bar", RemainingKeys(NotStrRe("tag2")): AnyOptStr()},
            command="PRIVMSG",
            params=["#chan", "hello"],
        ),
        # matches:
        [
            "@tag1=bar PRIVMSG #chan :hello",
            "@tag1=bar :foo!baz@qux PRIVMSG #chan :hello",
            "@tag1=bar;tag3= PRIVMSG #chan :hello",
        ],
        # and does not match:
        [
            "PRIVMG #chan :hello",
            "@tag1=value1 PRIVMSG #chan :hello",
            "@tag1=bar;tag2= PRIVMSG #chan :hello",
            "@tag1=bar;tag2=baz PRIVMSG #chan :hello",
        ]
    ),
    (
        # the specification:
        dict(
            command="005",
            params=["nick", "FOO=1", *ANYLIST],
        ),
        # matches:
        [
            "005 nick FOO=1",
            "005 nick FOO=1 BAR=2",
        ],
        # and does not match:
        [
            "005 nick",
            "005 nick BAR=2",
        ]
    ),
    (
        # the specification:
        dict(
            command="005",
            params=["nick", ListRemainder(ANYSTR, min_length=1)],
        ),
        # matches:
        [
            "005 nick FOO=1",
            "005 nick FOO=1 BAR=2",
            "005 nick BAR=2",
        ],
        # and does not match:
        [
            "005 nick",
        ]
    ),
    (
        # the specification:
        dict(
            command="005",
            params=["nick", ListRemainder(StrRe("[A-Z]+=.*"), min_length=1)],
        ),
        # matches:
        [
            "005 nick FOO=1",
            "005 nick FOO=1 BAR=2",
            "005 nick BAR=2",
        ],
        # and does not match:
        [
            "005 nick",
            "005 nick foo=1",
        ]
    ),
]
# fmt: on


class IrcTestCaseTestCase(cases._IrcTestCase):
    @pytest.mark.parametrize(
        "spec,msg",
        [
            pytest.param(spec, msg, id=f"{spec}-{msg}")
            for (spec, positive_matches, _) in MESSAGE_SPECS
            for msg in positive_matches
        ],
    )
    def test_message_matching_positive(self, spec, msg):
        assert not self.messageDiffers(parse_message(msg), **spec), msg
        assert self.messageEqual(parse_message(msg), **spec), msg
        self.assertMessageMatch(parse_message(msg), **spec), msg

    @pytest.mark.parametrize(
        "spec,msg",
        [
            pytest.param(spec, msg, id=f"{spec}-{msg}")
            for (spec, _, negative_matches) in MESSAGE_SPECS
            for msg in negative_matches
        ],
    )
    def test_message_matching_negative(self, spec, msg):
        assert self.messageDiffers(parse_message(msg), **spec), msg
        assert not self.messageEqual(parse_message(msg), **spec), msg
        with pytest.raises(AssertionError):
            self.assertMessageMatch(parse_message(msg), **spec), msg
