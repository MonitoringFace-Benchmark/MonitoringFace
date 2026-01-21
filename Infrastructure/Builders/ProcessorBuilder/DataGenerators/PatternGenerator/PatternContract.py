from dataclasses import fields, dataclass
from typing import Optional, Dict, Any

from Infrastructure.DataTypes.Contracts.AbstractContract import AbstractContract


@dataclass
class PatternContract(AbstractContract):
    def default_contract(self):
        return PatternContract(
            trace_length=1000, seed=None, event_rate=1000, index_rate=None, time_stamp=None, linear=1, interval=None,
            star=None, triangle=None, pattern=None, violations=1.0, zipf="x=1.5+3,z=2", prob_a=0.2,  prob_b=0.3, prob_c=0.5
        )

    def instantiate_contract(self, params: Dict[str, Any]):
        if not params:
            self.default_contract()
        else:
            valid_field_names = {f.name for f in fields(self)}
            for key, value in params.items():
                if key in valid_field_names:
                    setattr(self, key, value)
        return self

    trace_length: int = 1000
    seed: Optional[int] = None
    event_rate: int = 1000
    index_rate: Optional[int] = None
    time_stamp: Optional[int] = None

    star: Optional = None
    linear: Optional = 1
    triangle: Optional = None
    pattern: Optional[str] = None

    violations: Optional[float] = 1.0
    interval: Optional[str] = None
    zipf: str = "x=1.5+3,z=2"

    prob_a: float = 0.2
    prob_b: float = 0.3
    prob_c: float = 0.5


def patterns_to_commands(contract: PatternContract) -> list[str]:
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


def pattern_contract_to_commands(contract_params: Dict[str, Any]) -> list[str]:
    valid_fields = {f.name for f in fields(PatternContract)}
    contract = PatternContract(**{k: v for k, v in contract_params.items() if k in valid_fields})
    return patterns_to_commands(contract)

