from dataclasses import dataclass, fields
from typing import Optional, Dict, Any

from Infrastructure.DataTypes.Contracts.AbstractContract import AbstractContract


@dataclass
class SignatureContract(AbstractContract):
    def default_contract(self):
        return SignatureContract(
            trace_length=1000, seed=None, event_rate=1000, index_rate=None, time_stamp=None,
            sig="", sample_queue=None, string_length=None, fresh_value_rate=None, domain=None
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

    trace_length: int
    seed: Optional[int]
    event_rate: int
    index_rate: Optional[int]
    time_stamp: Optional[int]

    sig: str
    sample_queue: Optional[int]
    fresh_value_rate: Optional[float]
    domain: Optional[int]
    string_length: Optional[int]


def signature_to_commands(contract: SignatureContract) -> list[str]:
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


def signature_contract_to_commands(contract_params: Dict[str, Any]) -> list[str]:
    valid_fields = {f.name for f in fields(SignatureContract)}
    contract = SignatureContract(**{k: v for k, v in contract_params.items() if k in valid_fields})
    return signature_to_commands(contract)
