from typing import AnyStr, Dict, Tuple

from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats
from Infrastructure.Builders.ProcessorBuilder.PolicyGenerators.PolicyGeneratorTemplate import PolicyGeneratorTemplate


class ImmediatePolicyGenerator(PolicyGeneratorTemplate):
    def __init__(self, name, path_to_build):
        super().__init__()

    def generate_policy(self, policy_contract, time_on=None, time_out=None):
        seed, policy, sig = immediate_to_policy(policy_contract)
        return seed, policy, sig

    # TODO: This should be determined by the contract, not hardcoded here.
    @staticmethod
    def output_format() -> InputOutputPolicyFormats:
        return InputOutputPolicyFormats.MFOTL 


def immediate_to_policy(policy_contract: Dict) -> Tuple[int, str, str]:
    delimiter = policy_contract.get("delimiter") or ";"

    formulas = policy_contract.get("formulas")
    
    if not formulas:
        raise ValueError("ImmediatePolicyGenerator requires at least one named formula entry.")

    index = policy_contract.get("seed", 0) % len(formulas)
    payload = list(formulas.items())[index]
    selected_formula_name, payload = payload
    if delimiter not in payload:
        raise ValueError(
            f"Immediate formula '{selected_formula_name}' must contain delimiter '{delimiter}' between signature and formula."
        )

    sig, policy = payload.split(delimiter, 1)
    sig = sig.strip()
    policy = policy.strip()

    if not sig or not policy:
        raise ValueError(
            f"Immediate formula '{selected_formula_name}' must provide both a signature and a formula."
        )

    seed = policy_contract.get("seed", 0)
    return seed, policy, sig
