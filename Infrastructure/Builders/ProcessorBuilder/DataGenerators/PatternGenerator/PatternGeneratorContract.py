from dataclasses import fields, dataclass
from typing import AnyStr, Optional

from Infrastructure.DataTypes.Contracts.AbstractContract import AbstractContract


@dataclass
class Patterns(AbstractContract):
    def default_contract(self):
        return Patterns(
            trace_length=1000, seed=None, event_rate=1000, index_rate=None, time_stamp=None, linear=1, interval=None,
            star=None,triangle=None,pattern=None,violations=1.0,zipf="x=1.5+3,z=2", prob_a=0.2,  prob_b=0.3, prob_c=0.5
        )

    def instantiate_contract(self, params):
        if not params:
            return self.default_contract()
        valid_field_names = {f.name for f in fields(self)}
        for key, value in params.items():
            if key in valid_field_names:
                setattr(self, key, value)

    trace_length: int
    seed: Optional[int]
    event_rate: int
    index_rate: Optional[int]
    time_stamp: Optional[int]

    star: Optional
    linear: Optional
    triangle: Optional
    pattern: Optional[AnyStr]

    violations: Optional[float]
    interval: Optional[AnyStr]
    zipf: AnyStr

    prob_a: float
    prob_b: float
    prob_c: float


def patterns_to_commands(contract):
    args = []
    if contract.seed is not None:
        args.extend(["-seed", str(contract.seed)])
    args.extend(["-e", str(contract.event_rate)])
    if contract.index_rate is not None:
        args.extend(["-i", str(contract.index_rate)])
    if contract.time_stamp is not None:
        args.extend(["-t", str(contract.time_stamp)])
    if contract.star is not None:
        args.append("-S")
    elif contract.linear is not None:
        args.append("-L")
    elif contract.triangle is not None:
        args.append("-T")
    elif contract.pattern is not None:
        args.extend(["-P", contract.pattern])
    if contract.violations is not None:
        args.extend(["-x", str(contract.violations)])
    if contract.interval is not None:
        args.extend(["-w", str(contract.interval)])
    args.extend(["-pA", str(contract.prob_a)])
    args.extend(["-pB", str(contract.prob_b)])
    args.extend(["-z", contract.zipf])
    args.append(str(contract.trace_length))

    return args


def pattern_contract_to_commands(contract_params) -> list[AnyStr]:
    valid_fields = {f.name for f in fields(Patterns)}
    contract = Patterns(**{k: v for k, v in contract_params.items() if k in valid_fields})
    return patterns_to_commands(contract)

