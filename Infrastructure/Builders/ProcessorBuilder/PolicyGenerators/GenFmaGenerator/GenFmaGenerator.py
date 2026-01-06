import sys
from typing import AnyStr, Tuple

from Infrastructure.Builders.ProcessorBuilder.ImageManager import ImageManager
from Infrastructure.Builders.ProcessorBuilder.PolicyGenerators.GenFmaGenerator.GenFmaContract import GenFmaContract
from Infrastructure.Builders.ProcessorBuilder.PolicyGenerators.PolicyGeneratorTemplate import PolicyGeneratorTemplate
from Infrastructure.DataTypes.Types.custome_type import Processor
from Infrastructure.Monitors.MonitorExceptions import GeneratorException
from Infrastructure.constants import COMMAND_KEY


class GenFmaGenerator(PolicyGeneratorTemplate):
    def __init__(self, name, path_to_build):
        self.image = ImageManager(name, Processor.PolicyGenerators, path_to_build)

    def generate_policy(self, policy_contract_params, time_on=None, time_out=None):
        policy_contract = GenFmaContract().instantiate_contract(policy_contract_params)
        inner_dict = dict()
        inner_dict[COMMAND_KEY] = policy_contract_to_commands(policy_contract)
        out, code = self.image.run(inner_dict, time_on=time_on, time_out=time_out)
        if code != 0:
            raise GeneratorException()
        else:
            return parse_gen_output(policy_contract.seed, out), code


def parse_gen_output(seed, out: AnyStr) -> Tuple[int, str, str]:
    parts = out.strip().split("SIGNATURE:")
    sig_and_formula = parts[1].strip()

    sig_part, formula_part = sig_and_formula.split("MFOTL FORMULA:")
    sig = sig_part.strip()
    formula = formula_part.strip()
    return seed, sig, formula


def policy_contract_to_commands(f_contract: GenFmaContract) -> list:
    args = []

    args += ["-size", str(f_contract.size)]
    args += ["-free_vars", str(f_contract.free_vars)]

    if f_contract.sig is not None:
        args += ["-sig", str(f_contract.sig)]

    if f_contract.sig_file is not None:
        args += ["-sig_file", str(f_contract.sig_file)]

    if f_contract.seed is not None:
        args += ["-seed", str(f_contract.seed)]

    args += ["-max_lb", str(f_contract.max_lb)]
    args += ["-max_interval", str(f_contract.max_interval)]

    if f_contract.past_only:
        args += ["-past_only"]

    if f_contract.all_rels:
        args += ["-all_rels"]

    if f_contract.qtl:
        args += ["-qtl"]

    if f_contract.nolet:
        args += ["-nolet"]

    if f_contract.debug:
        args += ["-debug"]

    if f_contract.aggr:
        args += ["-aggr"]

    if f_contract.fo_only:
        args += ["-fo_only"]

    if f_contract.non_di:
        args += ["-non-di"]

    args += ["-max_const", str(f_contract.max_const)]
    return args
