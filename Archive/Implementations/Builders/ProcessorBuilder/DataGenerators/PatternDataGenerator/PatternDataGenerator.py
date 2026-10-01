from typing import AnyStr, List

from Archive.Implementations.Builders.ProcessorBuilder.DataGenerators.PatternDataGenerator.PatternDataContract import \
    pattern_contract_to_commands
from Infrastructure.Builders.ProcessorBuilder.DataGenerators.DataGeneratorTemplate import DataGeneratorTemplate
from Infrastructure.Builders.ProcessorBuilder.DataGenerators.WatermarkInfusion import infuse_watermarks
from Infrastructure.Builders.ProcessorBuilder.ImageManager import ImageManager, Processor
from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats
from Infrastructure.Monitors.MonitorExceptions import GeneratorException
from Infrastructure.constants import COMMAND_KEY, ENTRYPOINT_KEY


# Initial Value taken from the original repository
DEFAULT_SEED = 314159265


class PatternDataGenerator(DataGeneratorTemplate):
    def __init__(self, name, path_to_build):
        self.image = ImageManager(name, Processor.DataGenerators, path_to_build)

    def run_generator(self, contract_inner, time_on=None, time_out=None):
        seed_raw = contract_inner.get("seed")
        seed = seed_raw if seed_raw is not None else DEFAULT_SEED
        contract_with_seed = dict(contract_inner)
        contract_with_seed["seed"] = seed

        inner_contract = dict()
        inner_contract[COMMAND_KEY] = (["java", "-cp", "classes:libs/*", "org.entry.Dispatcher", "Generator"]
                                       + pattern_contract_to_commands(contract_with_seed))
        inner_contract[ENTRYPOINT_KEY] = ""
        out, code = self.image.run(inner_contract, time_on=time_on, time_out=time_out)

        if code != 0:
            raise GeneratorException(f"Pattern generator failed (exit_code={code}). Output:\n{out}")
        if contract_inner.get("watermarks"):
            out = infuse_watermarks(out)
        return seed, out

    def check_policy(self, path_inner: AnyStr, signature, formula) -> bool:
        return True

    @staticmethod
    def output_format() -> InputOutputTraceFormats:
        return InputOutputTraceFormats.CSV
