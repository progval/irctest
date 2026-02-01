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
    ACCOUNT_NOTIFY = "account-notify"
    ACCOUNT_TAG = "account-tag"
    AWAY_NOTIFY = "away-notify"
    BATCH = "batch"
    ECHO_MESSAGE = "echo-message"
    EXTENDED_JOIN = "extended-join"
    EXTENDED_MONITOR = "extended-monitor"
    LABELED_RESPONSE = "labeled-response"
    MESSAGE_REDACTION = "draft/message-redaction"
    MESSAGE_TAGS = "message-tags"
    MULTILINE = "draft/multiline"
    MULTI_PREFIX = "multi-prefix"
    SERVER_TIME = "server-time"
    SETNAME = "setname"
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
    ELIST = "ELIST"
    INVEX = "INVEX"
    PREFIX = "PREFIX"
    MONITOR = "MONITOR"
    STATUSMSG = "STATUSMSG"
    TARGMAX = "TARGMAX"
    UTF8ONLY = "UTF8ONLY"
    WHOX = "WHOX"

    @classmethod
    def from_name(cls, name: str) -> IsupportTokens:
        try:
            return cls(name.upper())
        except ValueError:
            raise ValueError(name) from None


@enum.unique
class OptionalBehaviors(enum.Enum):
    # NO_CTCP is the widely implemented +C mode that blocks CTCPs
    # (other than ACTION) from being sent to a channel.
    NO_CTCP = "+C no-CTCP mode"

    # CAP_REQ_MINUS is the ability to disable capabilities at runtime:
    # "Each capability identifier may be prefixed with a dash (-)
    #  to designate that the capability should be disabled."
    CAP_REQ_MINUS = "`CAP REQ -capname` to disable `capname`"

    # INVITE_OVERRIDES_LIMIT is the behavior where INVITE allows the invited
    # user to join a channel, even though their JOIN would put the channel
    # over the user limit count set with the +l channel mode.
    INVITE_OVERRIDES_LIMIT = "INVITE overrides the +l user limit channel mode"
