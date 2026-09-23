from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Strength(Enum):
    UNSUPPORTED = "unsupported"
    NONE = "none"
    CONSISTENT = "consistent"
    SUBSET = "subset"
    EQUIVALENT = "equivalent"


_RANK = {
    Strength.UNSUPPORTED: 0,
    Strength.NONE: 1,
    Strength.CONSISTENT: 2,
    Strength.SUBSET: 3,
    Strength.EQUIVALENT: 4,
}

GATEABLE = (Strength.CONSISTENT, Strength.SUBSET, Strength.EQUIVALENT)


def rank(strength: Strength) -> int:
    return _RANK[strength]


def parse_strength(name: str) -> Strength:
    for strength in Strength:
        if strength.value == name:
            return strength
    raise ValueError(f"Unknown verification strength {name!r}")


@dataclass(frozen=True)
class Comparison:
    """Outcome of one oracle/tool comparison.

    `strength` records what the relation is capable of establishing, which
    differs per structure pair and is otherwise invisible in the results: an
    EQUIVALENT relation proves the outputs agree, SUBSET only that the tool
    claimed nothing the oracle denies, CONSISTENT only that a declared set of
    positive and negative witnesses holds. The counters record what the
    relation actually inspected, so a relation that establishes nothing cannot
    look like one that did.

    Iterating yields (ok, message), so existing `verified, msg = ...` call
    sites keep working; that shim goes once they read the fields.
    """

    ok: bool
    message: str
    strength: Strength = Strength.NONE
    time_points_checked: int = 0
    values_checked: int = 0

    def __iter__(self):
        return iter((self.ok, self.message))

    def meets(self, minimum: Optional[Strength]) -> bool:
        return minimum is None or rank(self.strength) >= rank(minimum)

    def summary(self) -> str:
        return (f"{self.strength.value}, {self.values_checked} values over "
                f"{self.time_points_checked} time points")
