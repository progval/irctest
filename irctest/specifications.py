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
    BAN_EXCEPTION_MODE = "+e ban exception list channel mode"
    """
    Widely implemented channel mode +I, taking a list of NUH masks
    that are allowed to join the channel even if they match a mask
    in the +b ban list.
    """

    CAP_REQ_MINUS = "`CAP REQ -capname` to disable `capname`"
    """
    Ability to disable capabilities at runtime:
    Each capability identifier may be prefixed with a dash (-)
    to designate that the capability should be disabled.
    """

    INVITE_EXCEPTION_MODE = "+I invite exception list channel mode"
    """
    Widely implemented channel mode +I, taking a list of NUH masks
    that are always considered invited to the channel (bypassing the +i
    invite-only mode).
    """

    INVITE_LIST = "INVITE with no parameters lists active invites"
    """
    Some ircd implementations accept INVITE with no parameters and
    return a list of the user's active invites, using the 336/337 numerics.
    """

    INVITE_OVERRIDES_LIMIT = "INVITE overrides the +l user limit channel mode"
    """
    Support for the INVITE command allowing the invited user to join a channel,
    even though their JOIN would put the channel over the user limit count set
    with the +l channel mode.
    """

    METADATA_BEFORE_CONNECT = "draft/metadata-2=before-connect"
    """
    Optional feature in draft/metadata-2 allowing clients to set metadata
    on themselves before completing connection registration.
    """

    MULTI_JOIN = "JOIN multiple channels with one command"
    """
    Ability to JOIN multiple channels on a single JOIN line, e.g.
    `JOIN #baz,#bat`; see https://modern.ircdocs.horse/#targmax-parameter
    for context.
    """

    MULTI_KICK = "KICK multiple users with one command"
    """
    Ability to KICK multiple channels on a single KICK line, e.g.
    `KICK #baz alice,bob`; see https://modern.ircdocs.horse/#targmax-parameter
    for context.
    """

    MULTI_NAMES_COMMAND = "NAMES command supports requesting multiple channels"
    """
    Ability to request membership lists for multiple channels on a single
    NAMES line, e.g. `NAMES #baz,bat`; see
    https://modern.ircdocs.horse/#targmax-parameter for context.
    """

    MULTI_PRIVMSG = "PRIVMSG multiple targets with one command"
    """
    Ability to PRIVMSG multiple targets on a single PRIVMSG line, e.g.
    `PRIVMSG alice,bob :hi there`; see
    https://modern.ircdocs.horse/#targmax-parameter for context.
    """

    NO_CTCP = "+C no-CTCP mode"
    """
    Widely implemented +C mode that blocks CTCPs
    (other than ACTION) from being sent to a channel.
    """

    SASL_AFTER_REGISTRATION = "SASL after registration"
    """
    Support for clients sending AUTHENTICATE messages when they are already registered
    (https://ircv3.net/specs/extensions/sasl-3.2#sasl-reauthentication).

    Not to be confused with SASL_REAUTHENTICATION which is for clients that are both
    registered and authenticated.
    """

    SASL_REAUTHENTICATION = "SASL re-authentication"
    """
    Support for clients sending AUTHENTICATE messages when they are already authenticated
    (https://ircv3.net/specs/extensions/sasl-3.2#sasl-reauthentication)
    """

    ELIST_M = "ELIST=M (filtering LIST output based on mask)"
    """
    Filtering the LIST output based on mask.
    https://modern.ircdocs.horse/#elist-parameter
    """

    ELIST_N = "ELIST=N (filtering LIST output based on non-matching mask)"
    """
    Filtering the LIST output based on a non-matching mask (the opposite of M).
    https://modern.ircdocs.horse/#elist-parameter
    """

    ELIST_U = "ELIST=U (filtering LIST output based on user count)"
    """
    Filtering the LIST output based on user count within the channel, via the
    "<val" and ">val" modifiers to filter for channels that have less or more
    than val users, respectively.
    https://modern.ircdocs.horse/#elist-parameter
    """

    ELIST_C = "ELIST=C (filtering LIST output based on channel creation time)"
    """
    Filtering the LIST output based on channel creation time, via the "C<val"
    and "C>val" modifiers to filter for channels that were created either less
    than val minutes ago, or more than val minutes ago, respectively.
    https://modern.ircdocs.horse/#elist-parameter
    """

    ELIST_T = "ELIST=T (filtering LIST output based on topic set time)"
    """
    Filtering the LIST output based on topic set time, via the "T<val" and
    "T>val" modifiers to filter for channels whose topic was set less than val
    minutes ago, or more than val minutes ago, respectively.
    https://modern.ircdocs.horse/#elist-parameter
    """
