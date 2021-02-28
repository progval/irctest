import dataclasses
import enum
from typing import Optional, Tuple


@enum.unique
class Mechanisms(enum.Enum):
    """Enumeration for representing possible mechanisms."""

    def to_string(self) -> str:
        return self.name.upper().replace("_", "-")

    plain = 1
    ecdsa_nist256p_challenge = 2
    scram_sha_256 = 3


@dataclasses.dataclass
class Authentication:
    mechanisms: Tuple[Mechanisms] = (Mechanisms.plain,)
    username: Optional[str] = None
    password: Optional[str] = None
    ecdsa_key: Optional[str] = None
