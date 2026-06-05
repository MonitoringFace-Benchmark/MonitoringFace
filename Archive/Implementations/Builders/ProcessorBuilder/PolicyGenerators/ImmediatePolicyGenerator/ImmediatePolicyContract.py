from dataclasses import dataclass, field
from typing import Dict

from Infrastructure.AutoConversion.InputOutputPolicyFormats import str_to_policy_inout_format
from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats
from Infrastructure.DataTypes.Contracts.AbstractContract import AbstractContract


@dataclass
class ImmediatePolicyContract(AbstractContract):
    def default_contract(self):
        self.policyformat = str_to_policy_inout_format(self.format)
        return self

    def instantiate_contract(self, params):
        self.default_contract()
        if not params:
            return self

        reserved_keys = {"seed", "format", "delimiter"}
        for key, value in params.items():
            if key == "seed" and value is not None:
                self.seed = int(value)
            elif key == "format" and value is not None:
                self.format = value
            elif key == "delimiter" and value is not None:
                self.delimiter = value
            elif key not in reserved_keys and isinstance(value, str):
                # Any extra key under ImmediatePolicyContract is treated as named formula content.
                self.formulas[key] = value

        self.policyformat = str_to_policy_inout_format(self.format)
        return self

    seed: int = 42
    format: str = "MFOTL"
    delimiter: str = ";"
    policyformat: InputOutputPolicyFormats = InputOutputPolicyFormats.MFOTL
    formulas: Dict[str, str] = field(default_factory=dict)