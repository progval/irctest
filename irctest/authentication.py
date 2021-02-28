import dataclasses
import enum
from typing import Optional, Tuple


@enum.unique
class Mechanisms(enum.Enum):
    """Enumeration for representing possible mechanisms."""

    @classmethod
    def as_string(cls, mech):
        return {
            cls.plain: "PLAIN",
            cls.ecdsa_nist256p_challenge: "ECDSA-NIST256P-CHALLENGE",
            cls.scram_sha_256: "SCRAM-SHA-256",
        }[mech]

    plain = 1
    ecdsa_nist256p_challenge = 2
    scram_sha_256 = 3


@dataclasses.dataclass
class Authentication:
    mechanisms: Tuple[Mechanisms] = (Mechanisms.plain,)
    username: Optional[str] = None
    password: Optional[str] = None
    ecdsa_key: Optional[str] = None
