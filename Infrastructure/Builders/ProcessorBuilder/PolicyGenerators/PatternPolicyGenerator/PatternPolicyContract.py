from dataclasses import dataclass, fields
from typing import AnyStr, Optional, Any

from Infrastructure.DataTypes.Contracts.AbstractContract import AbstractContract


@dataclass
class PatternPolicyContract(AbstractContract):
    def __init__(self):
        pass

    def default_contract(self):
        return PatternPolicyContract(interval="[0,30)", policy="linear")

    def instantiate_contract(self, params):
        if not params:
            self.default_contract()
        else:
            valid_field_names = {f.name for f in fields(self)}
            for key, value in params.items():
                if key in valid_field_names:
                    setattr(self, key, value)
        return self

    interval: Optional[str]
    policy: Optional[str]
