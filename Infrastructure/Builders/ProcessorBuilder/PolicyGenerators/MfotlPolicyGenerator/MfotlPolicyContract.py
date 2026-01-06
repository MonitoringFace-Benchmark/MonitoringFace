from dataclasses import dataclass, fields
from typing import Optional, AnyStr

from Infrastructure.DataTypes.Contracts.AbstractContract import AbstractContract


@dataclass
class MfotlPolicyContract(AbstractContract):
    def __init__(self):
        pass

    def default_contract(self):
        return MfotlPolicyContract()

    def instantiate_contract(self, params):
        if not params:
            return self.default_contract()
        valid_field_names = {f.name for f in fields(self)}
        for key, value in params.items():
            if key in valid_field_names:
                setattr(self, key, value)
        return self

    sig_file: Optional[str] = None
    out_file: Optional[str] = None
    seed: Optional[int] = None
    size: Optional[int] = None

    num_preds: int = 4
    max_arity: int = 4
    non_zero: bool = False

    aggregation: bool = False

    prob_and: Optional[float] = None
    prob_or: Optional[float] = None
    prob_eand: Optional[float] = None
    prob_nand: Optional[float] = None
    prob_rand: Optional[float] = None

    prob_prev: Optional[float] = None
    prob_once: Optional[float] = None
    prob_next: Optional[float] = None
    prob_eventually: Optional[float] = None
    prob_since: Optional[float] = None
    prob_until: Optional[float] = None

    prob_exists: Optional[float] = None
    prob_let: Optional[float] = None
    prob_aggreg: Optional[float] = None

    regex: bool = False
    prob_matchP: Optional[float] = None
    prob_matchF: Optional[float] = None


def policy_contract_to_commands(f_contract: MfotlPolicyContract) -> list[AnyStr]:
    args = []

    args += ["-pred", str(f_contract.num_preds)]
    args += ["-A", str(f_contract.max_arity)]

    if f_contract.non_zero:
        args += ["-nonzero"]

    if f_contract.sig_file is not None:
        args += ["-sig", str(f_contract.sig_file)]

    if f_contract.seed is not None:
        args += ["-seed", str(f_contract.seed)]

    if f_contract.size is not None:
        args += ["-S", str(f_contract.size)]

    if f_contract.aggregation:
        args += ["-agg"]

    if f_contract.prob_and is not None:
        args += ["-prob_and", str(f_contract.prob_and)]

    if f_contract.prob_or is not None:
        args += ["-prob_or", str(f_contract.prob_or)]

    if f_contract.prob_prev is not None:
        args += ["-prob_prev", str(f_contract.prob_prev)]

    if f_contract.prob_once is not None:
        args += ["-prob_once", str(f_contract.prob_once)]

    if f_contract.prob_next is not None:
        args += ["-prob_next", str(f_contract.prob_next)]

    if f_contract.prob_eventually is not None:
        args += ["-prob_eventually", str(f_contract.prob_eventually)]

    if f_contract.prob_since is not None:
        args += ["-prob_since", str(f_contract.prob_since)]

    if f_contract.prob_until is not None:
        args += ["-prob_until", str(f_contract.prob_until)]

    if f_contract.prob_rand is not None:
        args += ["-prob_rand", str(f_contract.prob_rand)]

    if f_contract.prob_eand is not None:
        args += ["-prob_eand", str(f_contract.prob_eand)]

    if f_contract.prob_nand is not None:
        args += ["-prob_nand", str(f_contract.prob_nand)]

    if f_contract.prob_exists is not None:
        args += ["-prob_exists", str(f_contract.prob_exists)]

    if f_contract.prob_let is not None:
        args += ["-prob_let", str(f_contract.prob_let)]

    if f_contract.prob_aggreg is not None:
        args += ["-prob_aggreg", str(f_contract.prob_aggreg)]

    if f_contract.regex:
        args += ["-regex"]

    if f_contract.prob_matchP is not None:
        args += ["-prob_matchP", str(f_contract.prob_matchP)]

    if f_contract.prob_matchF is not None:
        args += ["-prob_matchF", str(f_contract.prob_matchF)]

    return args
