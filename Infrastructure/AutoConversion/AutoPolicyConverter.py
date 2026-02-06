import os
import shutil
from typing import List


from Infrastructure.AutoConversion.AutoConversionMapping import AutoConversionMapping
from Infrastructure.Builders.ProcessorBuilder.PolicyConverters.PolicyConverterTemplate import PolicyConverterTemplate
from Infrastructure.DataTypes.PathManager.PathManager import PathManager
from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats


class PolicyConversionError(Exception):
    pass


class AutoPolicyConverter:
    def __init__(self, path_manager: PathManager, source_format: InputOutputPolicyFormats, target_format: InputOutputPolicyFormats):
        self.source_format = source_format
        self.target_format = target_format
        self.path_manager = path_manager

    def _conversion_chain(self) -> List[PolicyConverterTemplate]:
        auto_conversion_mapping = AutoConversionMapping(self.path_manager, "PolicyConverters")
        converter_chain = []
        for converter_name, converter_class, source, target in auto_conversion_mapping.resolve_format(self.source_format, self.target_format):
            try:
                converter_chain.append((converter_class(converter_name, self.path_manager.get_path("path_to_project")), source, target))
            except Exception as e:
                raise PolicyConversionError(f"AutoPolicyConverter: Failed to initialize converter: {e}")
        return converter_chain

    @staticmethod
    def reachable(path_manager, source, target) -> bool:
        try:
            AutoConversionMapping(path_manager, "PolicyConverters").resolve_format(source, target)
            return True
        except Exception():
            return False

    def convert(self, input_file: str, output_file: str, params) -> str:
        pass


if __name__ == "__main__":
    from Infrastructure.DataTypes.PathManager.PathManager import PathManager
    pm = PathManager()
    pm.add_path("path_to_project", "/Users/krq770/PycharmProjects/MonitoringFace_curr")
    pm.add_path("path_to_infrastructure", "/Users/krq770/PycharmProjects/MonitoringFace_curr/Infrastructure")

    #x = _discover_trace_converters("/Users/krq770/PycharmProjects/MonitoringFace_curr/Infrastructure")
    #mapping_ = {
    #    (InputOutputTraceFormats.OOO_CSV, InputOutputTraceFormats.CSV): ["OrderRestorerConverter"],
    #    (InputOutputTraceFormats.CSV, InputOutputTraceFormats.MONPOLY): ["MonpolyConverter"],
    #}
    #ag = AutoConversionReachabilityGraph(mapping_)
    #x = ag.find_path(InputOutputTraceFormats.OOO_CSV, InputOutputTraceFormats.MONPOLY)
    x = AutoConversionMapping(pm)
    print(x.mappings)