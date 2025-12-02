from dataclasses import fields
from typing import AnyStr

from Infrastructure.Builders.ProcessorBuilder.ImageManager import ImageManager, Processor
from Infrastructure.Builders.ProcessorBuilder.PolicyGenerators.MfotlPolicyGenerator.MfotlPolicyContract import MfotlPolicyContract
from Infrastructure.Builders.ProcessorBuilder.PolicyGenerators.MfotlPolicyGenerator.MfotlPolicyContract import \
    policy_contract_to_commands
from Infrastructure.Builders.ProcessorBuilder.PolicyGenerators.PolicyGeneratorTemplate import PolicyGeneratorTemplate
from Infrastructure.Monitors.MonitorExceptions import GeneratorException
from Infrastructure.constants import COMMAND_KEY, ENTRYPOINT_KEY


class MfotlPolicyGenerator(PolicyGeneratorTemplate):
    def __init__(self, name, path_to_build):
        self.image = ImageManager(name, Processor.PolicyGenerators, path_to_build)

    def generate_policy(self, policy_contract_params, time_on=None, time_out=None):
        valid_fields = {f.name for f in fields(MfotlPolicyContract)}
        policy_contract = MfotlPolicyContract(
            **{k: v for k, v in policy_contract_params.items() if k in valid_fields})

        inner_dict = dict()
        inner_dict[COMMAND_KEY] = ["python3", "gen_for.py"] + policy_contract_to_commands(policy_contract)
        inner_dict[ENTRYPOINT_KEY] = ""
        out, code = self.image.run(inner_dict, time_on=time_on, time_out=time_out)
        if code != 0:
            raise GeneratorException()
        else:
            return parse_gen_output(out), code


def parse_gen_output(st: AnyStr):
    _, lines = st.split("Seed:")
    res, lines = lines.split("Signature:")
    seed = res.replace(" ⎯⎯⎯⎯⎯", "").strip()
    res, lines = lines.split("MFOTL Formula:")
    sig = res.strip()
    formula = lines.strip()
    return seed, sig, formula
