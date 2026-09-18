import re
from typing import Dict, Optional, Tuple

Pin = Tuple[Optional[str], Optional[str]]

_pins: Dict[str, Pin] = {}


def set_pins(pins: Dict[str, Pin]) -> None:
    _pins.clear()
    _pins.update(pins)


def clear_pins() -> None:
    _pins.clear()


def get_pin(*names: Optional[str]) -> Pin:
    for name in names:
        if name and name in _pins:
            return _pins[name]
    return None, None


def all_pins() -> Dict[str, Pin]:
    return dict(_pins)


def docker_ref(ref: str) -> str:
    return re.sub(r"[^a-z0-9_.-]+", "-", str(ref).lower()).strip("-.") or "unversioned"
