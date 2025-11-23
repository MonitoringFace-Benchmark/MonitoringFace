from dataclasses import dataclass, fields
from typing import AnyStr, Optional


@dataclass
class Patterns:
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


def patterns_to_formula(pat) -> AnyStr:
    interval = pat["interval"] if pat["interval"] is not None else "[0,30)"
    if pat["linear"] is not None:
        return f"((ONCE {interval} A(w,x)) AND B(x,y)) AND (EVENTUALLY {interval} C(y,z))"
    elif pat["triangle"] is not None:
        return f"((ONCE {interval} A(x,y)) AND B(y,z)) AND (EVENTUALLY {interval} C(z,x))"
    else:
        return f"((ONCE {interval} A(w,x)) AND B(w,y)) AND (EVENTUALLY {interval} C(w,z))"


@dataclass
class Signature:
    trace_length: int
    seed: Optional[int]
    event_rate: int
    index_rate: Optional[int]
    time_stamp: Optional[int]

    sig: AnyStr
    sample_queue: Optional[int]
    fresh_value_rate: Optional[float]
    domain: Optional[int]
    string_length: Optional[int]


def signature_to_commands(contract):
    args = []
    if contract.seed is not None:
        args.extend(["-seed", str(contract.seed)])
    args.extend(["-e", str(contract.event_rate)])
    if contract.index_rate is not None:
        args.extend(["-i", str(contract.index_rate)])
    if contract.time_stamp is not None:
        args.extend(["-t", str(contract.time_stamp)])
    if contract.sig is not None:
        args.extend(["-sig", contract.sig])
    if contract.sample_queue is not None:
        args.extend(["-q", str(contract.sample_queue)])
    if contract.fresh_value_rate is not None:
        args.extend(["-r", str(contract.fresh_value_rate)])
    if contract.domain is not None:
        args.extend(["-dom", str(contract.domain)])
    if contract.string_length is not None:
        args.extend(["-strlen", str(contract.string_length)])
    args.append(str(contract.trace_length))

    return args


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


def data_contract_to_commands(contract_params) -> list[AnyStr]:
    try:
        valid_fields = {f.name for f in fields(Patterns)}
        contract = Patterns(**{k: v for k, v in contract_params.items() if k in valid_fields})
        return patterns_to_commands(contract)
    except Exception:
        pass

    try:
        valid_fields = {f.name for f in fields(Signature)}
        contract = Signature(**{k: v for k, v in contract_params.items() if k in valid_fields})
        return signature_to_commands(contract)
    except Exception:
        pass


@dataclass
class DataGolfContract:
    sig_file: AnyStr
    formula: AnyStr
    path: AnyStr

    trace_length: int
    oracle: bool

    no_rewrite: Optional[bool]
    tup_ts: list[int]
    tup_amt: int
    tup_val: int
