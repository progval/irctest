from typing import Dict, List, Optional


def cap_list_to_dict(caps: List[str]) -> Dict[str, Optional[str]]:
    d: Dict[str, Optional[str]] = {}
    for cap in caps:
        if "=" in cap:
            (key, value) = cap.split("=", 1)
            d[key] = value
        else:
            d[cap] = None
    return d
