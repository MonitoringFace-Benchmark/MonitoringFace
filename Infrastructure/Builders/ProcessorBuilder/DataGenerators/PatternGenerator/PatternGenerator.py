from typing import AnyStr

from Infrastructure.Builders.ProcessorBuilder.DataGenerators.DataGeneratorTemplate import DataGeneratorTemplate
from Infrastructure.Builders.ProcessorBuilder.DataGenerators.PatternGenerator.PatternContract import pattern_contract_to_commands
from Infrastructure.Builders.ProcessorBuilder.ImageManager import ImageManager, Processor
from Infrastructure.constants import COMMAND_KEY, ENTRYPOINT_KEY


# Initial Value taken from the original repository
DEFAULT_SEED = 314159265


class PatternGenerator(DataGeneratorTemplate):
    def __init__(self, name, path_to_build):
        self.image = ImageManager("gen_data", Processor.DataGenerators, path_to_build)

    def run_generator(self, contract_inner, time_on=None, time_out=None):
        inner_contract = dict()
        inner_contract[COMMAND_KEY] = (["java", "-cp", "classes:libs/*", "org.entry.Dispatcher", "Generator"]
                                       + pattern_contract_to_commands(contract_inner))
        inner_contract[ENTRYPOINT_KEY] = ""
        seed_raw = contract_inner["seed"]
        seed = seed_raw if seed_raw else DEFAULT_SEED
        out, code = self.image.run(inner_contract, time_on=time_on, time_out=time_out)
        return seed, out, code

    def check_policy(self, path_inner: AnyStr, signature, formula) -> bool:
        return True
