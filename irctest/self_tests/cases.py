"""Internal checks of assertion implementations."""

from typing import Dict, List, Tuple

import pytest

from irctest import cases
from irctest.irc_utils.message_parser import parse_message
from irctest.patma import (
    ANYDICT,
    ANYLIST,
    ANYOPTSTR,
    ANYSTR,
    ListRemainder,
    NotStrRe,
    OptStrRe,
    RemainingKeys,
    StrRe,
)

# fmt: off
MESSAGE_SPECS: List[Tuple[Dict, List[str], List[str], List[str]]] = [
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
        ],
        # and they each error with:
        [
            "expected params to match ['#chan', 'hello'], got ['#chan', 'hello2']",
            "expected params to match ['#chan', 'hello'], got ['#chan2', 'hello']",
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
        ],
        # and they each error with:
        [
            "expected params to match ['#chan', StrRe(r'hello.*')], got ['#chan', 'hi']",
            "expected params to match ['#chan', StrRe(r'hello.*')], got ['#chan2', 'hello']",
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
        ],
        # and they each error with:
        [
            "expected nick to be foo, got None instead",
            "expected nick to be foo, got foo2 instead",
            "expected nick to be foo, got foo2 instead",
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
        ],
        # and they each error with:
        [
            "expected tags to match {'tag1': 'bar'}, got {'tag1': 'bar', 'tag2': ''}",
            "expected tags to match {'tag1': 'bar'}, got {'tag1': 'value1'}",
            "expected tags to match {'tag1': 'bar'}, got {}",
            "expected tags to match {'tag1': 'bar'}, got {}",
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
        ],
        # and they each error with:
        [
            "expected tags to match {'tag1': ANYSTR}, got {'tag1': 'bar', 'tag2': ''}",
            "expected tags to match {'tag1': ANYSTR}, got {}",
            "expected tags to match {'tag1': ANYSTR}, got {}",
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
        ],
        # and they each error with:
        [
            "expected command to be PRIVMSG, got PRIVMG",
            "expected tags to match {'tag1': 'bar', RemainingKeys(ANYSTR): ANYOPTSTR}, got {'tag1': 'value1'}",
            "expected params to match ['#chan', 'hello'], got ['#chan', 'hello2']",
            "expected params to match ['#chan', 'hello'], got ['#chan2', 'hello']",
            "expected tags to match {'tag1': 'bar', RemainingKeys(ANYSTR): ANYOPTSTR}, got {}",
        ]
    ),
    (
        # the specification:
        dict(
            tags={StrRe("tag[12]"): "bar", **ANYDICT},
            command="PRIVMSG",
            params=["#chan", "hello"],
        ),
        # matches:
        [
            "@tag1=bar PRIVMSG #chan :hello",
            "@tag1=bar;tag2= PRIVMSG #chan :hello",
            "@tag1=bar :foo!baz@qux PRIVMSG #chan :hello",
            "@tag2=bar PRIVMSG #chan :hello",
            "@tag1=bar;tag2= PRIVMSG #chan :hello",
            "@tag1=;tag2=bar PRIVMSG #chan :hello",
        ],
        # and does not match:
        [
            "PRIVMG #chan :hello",
            "@tag1=value1 PRIVMSG #chan :hello",
            "PRIVMSG #chan hello2",
            "PRIVMSG #chan2 hello",
            ":foo!baz@qux PRIVMSG #chan hello",
        ],
        # and they each error with:
        [
            "expected command to be PRIVMSG, got PRIVMG",
            "expected tags to match {StrRe(r'tag[12]'): 'bar', RemainingKeys(ANYSTR): ANYOPTSTR}, got {'tag1': 'value1'}",
            "expected params to match ['#chan', 'hello'], got ['#chan', 'hello2']",
            "expected params to match ['#chan', 'hello'], got ['#chan2', 'hello']",
            "expected tags to match {StrRe(r'tag[12]'): 'bar', RemainingKeys(ANYSTR): ANYOPTSTR}, got {}",
        ]
    ),
    (
        # the specification:
        dict(
            tags={"tag1": "bar", RemainingKeys(NotStrRe("tag2")): ANYOPTSTR},
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
        ],
        # and they each error with:
        [
            "expected command to be PRIVMSG, got PRIVMG",
            "expected tags to match {'tag1': 'bar', RemainingKeys(NotStrRe(r'tag2')): ANYOPTSTR}, got {'tag1': 'value1'}",
            "expected tags to match {'tag1': 'bar', RemainingKeys(NotStrRe(r'tag2')): ANYOPTSTR}, got {'tag1': 'bar', 'tag2': ''}",
            "expected tags to match {'tag1': 'bar', RemainingKeys(NotStrRe(r'tag2')): ANYOPTSTR}, got {'tag1': 'bar', 'tag2': 'baz'}",
        ]
    ),
    (
        # the specification:
        dict(
            command="004",
            params=["nick", "...", OptStrRe("[a-zA-Z]+")],
        ),
        # matches:
        [
            "004 nick ... abc",
            "004 nick ...",
        ],
        # and does not match:
        [
            "004 nick ... 123",
            "004 nick ... :",
        ],
        # and they each error with:
        [
            "expected params to match ['nick', '...', OptStrRe(r'[a-zA-Z]+')], got ['nick', '...', '123']",
            "expected params to match ['nick', '...', OptStrRe(r'[a-zA-Z]+')], got ['nick', '...', '']",
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
        ],
        # and they each error with:
        [
            "expected params to match ['nick', 'FOO=1', *ANYLIST], got ['nick']",
            "expected params to match ['nick', 'FOO=1', *ANYLIST], got ['nick', 'BAR=2']",
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
        ],
        # and they each error with:
        [
            "expected params to match ['nick', ListRemainder(ANYSTR, min_length=1)], got ['nick']",
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
        ],
        # and they each error with:
        [
            "expected params to match ['nick', ListRemainder(StrRe(r'[A-Z]+=.*'), min_length=1)], got ['nick']",
            "expected params to match ['nick', ListRemainder(StrRe(r'[A-Z]+=.*'), min_length=1)], got ['nick', 'foo=1']",
        ]
    ),
    (
        # the specification:
        dict(
            command="PING",
            params=["abc"]
        ),
        # matches:
        [
            "PING abc",
        ],
        # and does not match:
        [
            "PONG def"
        ],
        # and they each error with:
        [
            "expected command to be PING, got PONG"
        ]
    ),
]
# fmt: on


class IrcTestCaseTestCase(cases._IrcTestCase):
    @pytest.mark.parametrize(
        "spec,msg",
        [
            pytest.param(spec, msg, id=f"{spec}-{msg}")
            for (spec, positive_matches, _, _) in MESSAGE_SPECS
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
            for (spec, _, negative_matches, _) in MESSAGE_SPECS
            for msg in negative_matches
        ],
    )
    def test_message_matching_negative(self, spec, msg):
        assert self.messageDiffers(parse_message(msg), **spec), msg
        assert not self.messageEqual(parse_message(msg), **spec), msg
        with pytest.raises(AssertionError):
            self.assertMessageMatch(parse_message(msg), **spec), msg

    @pytest.mark.parametrize(
        "spec,msg,error_string",
        [
            pytest.param(spec, msg, error_string, id=error_string)
            for (spec, _, negative_matches, error_stringgexps) in MESSAGE_SPECS
            for (msg, error_string) in zip(negative_matches, error_stringgexps)
        ],
    )
    def test_message_matching_negative_message(self, spec, msg, error_string):
        self.assertIn(error_string, self.messageDiffers(parse_message(msg), **spec))
