from dataclasses import dataclass
from typing import Tuple

from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats, str_to_policy_inout_format

ALTERNATIVE_SEPARATOR = "|"


@dataclass(frozen=True)
class PolicyAlternatives:
    """One property given in several policy formats, e.g. an MFOTL formula and
    a tool-native specification of the same property. Every consumer (tool,
    oracle, time guard) runs the alternative it reaches with the fewest
    conversion steps; on equal distance the earlier alternative wins."""

    options: Tuple[Tuple[str, InputOutputPolicyFormats], ...]

    def __post_init__(self):
        if len(self.options) < 2:
            raise ValueError("Policy alternatives need at least two options")
        formats = [fmt for _, fmt in self.options]
        if len(set(formats)) != len(formats):
            raise ValueError(
                f"Policy alternatives must have distinct formats, got "
                f"{', '.join(fmt.value for fmt in formats)}")

    def __str__(self):
        return f" {ALTERNATIVE_SEPARATOR} ".join(f"{file}: {fmt.value}" for file, fmt in self.options)


def parse_policy_alternatives(raw_value: str) -> PolicyAlternatives:
    options = []
    for part in raw_value.split(ALTERNATIVE_SEPARATOR):
        part = part.strip()
        if ":" not in part:
            raise ValueError(f"Policy alternative '{part}' has no format (expected 'file: format')")
        file, fmt = (piece.strip() for piece in part.split(":", 1))
        options.append((file, str_to_policy_inout_format(fmt)))
    return PolicyAlternatives(tuple(options))
