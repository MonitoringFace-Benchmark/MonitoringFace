from dataclasses import dataclass, fields
from typing import Optional

from Infrastructure.DataTypes.Contracts.AbstractContract import AbstractContract


@dataclass
class DataGolfContract(AbstractContract):
    def default_contract(self):
        return DataGolfContract(
            sig_file="", formula="", path="", seed=None, trace_length=10, oracle=False, no_rewrite=None,
            tup_ts=list(range(0, 5)), tup_amt=10, tup_val=0
        )

    def instantiate_contract(self, params):
        if not params:
            self.default_contract()
        else:
            valid_field_names = {f.name for f in fields(self)}
            for key, value in params.items():
                if key in valid_field_names:
                    setattr(self, key, value)
        return self

    sig_file: str
    formula: str
    path: str
    seed: Optional[int]

    trace_length: int
    oracle: bool

    no_rewrite: Optional[bool]
    tup_ts: list[int]
    tup_amt: int
    tup_val: int