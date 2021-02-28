import dataclasses
from typing import List


@dataclasses.dataclass
class TlsConfig:
    enable: bool
    trusted_fingerprints: List[str]
