from dataclasses import dataclass, fields
from typing import Optional

from Infrastructure.DataTypes.Contracts.AbstractContract import AbstractContract


@dataclass
class GenFmaContract(AbstractContract):
    def __init__(self):
        pass

    def instantiate_contract(self, params):
        if not params:
            self.default_contract()
        else:
            valid_field_names = {f.name for f in fields(self)}
            for key, value in params.items():
                if key in valid_field_names:
                    setattr(self, key, value)
        return self

    def default_contract(self):
        return GenFmaContract()

    size: int = 10
    free_vars: int = 3
    sig: Optional[str] = None
    sig_file: Optional[str] = None
    seed: int = 42
    max_lb: int = 5
    max_interval: int = 20
    past_only: bool = False
    all_rels: bool = False
    qtl: bool = False
    nolet: bool = False
    debug: bool = False
    aggr: bool = False
    fo_only: bool = False
    non_di: bool = False
    max_const: int = 42

