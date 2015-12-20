import enum
import collections

@enum.unique
class Mechanisms(enum.Enum):
    """Enumeration for representing possible mechanisms."""
    @classmethod
    def as_string(cls, mech):
        return {cls.plain: 'PLAIN',
                cls.ecdsa_nist256p_challenge: 'ECDSA-NIST256P-CHALLENGE',
                }[mech]
    plain = 1
    ecdsa_nist256p_challenge = 2

Authentication = collections.namedtuple('Authentication',
        'mechanisms username password ecdsa_key')
Authentication.__new__.__defaults__ = ([Mechanisms.plain], None, None, None)
