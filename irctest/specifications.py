from __future__ import annotations

import enum


@enum.unique
class Specifications(enum.Enum):
    RFC1459 = "RFC1459"
    RFC2812 = "RFC2812"
    IRCv3 = "IRCv3"  # Mark with capabilities whenever possible
    Ergo = "Ergo"

    Ircdocs = "ircdocs"
    """Any document on ircdocs.horse (especially defs.ircdocs.horse),
    excluding modern.ircdocs.horse"""

    Modern = "modern"

    @classmethod
    def from_name(cls, name: str) -> Specifications:
        name = name.upper()
        for spec in cls:
            if spec.value.upper() == name:
                return spec
        raise ValueError(name)


@enum.unique
class Capabilities(enum.Enum):
    ACCOUNT_TAG = "account-tag"
    AWAY_NOTIFY = "away-notify"
    BATCH = "batch"
    ECHO_MESSAGE = "echo-message"
    EXTENDED_JOIN = "extended-join"
    LABELED_RESPONSE = "labeled-response"
    MESSAGE_TAGS = "message-tags"
    MULTILINE = "draft/multiline"
    MULTI_PREFIX = "multi-prefix"
    SERVER_TIME = "server-time"
    STS = "sts"

    @classmethod
    def from_name(cls, name: str) -> Capabilities:
        try:
            return cls(name.lower())
        except ValueError:
            raise ValueError(name) from None


@enum.unique
class IsupportTokens(enum.Enum):
    BOT = "BOT"
    PREFIX = "PREFIX"
    MONITOR = "MONITOR"
    STATUSMSG = "STATUSMSG"
    TARGMAX = "TARGMAX"

    @classmethod
    def from_name(cls, name: str) -> IsupportTokens:
        try:
            return cls(name.upper())
        except ValueError:
            raise ValueError(name) from None
