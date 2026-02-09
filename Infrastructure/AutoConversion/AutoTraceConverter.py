import os
import shutil
from typing import List, Optional

from Infrastructure.AutoConversion.AutoConversionMapping import AutoConversionMapping
from Infrastructure.Builders.ProcessorBuilder.DataConverters.DataConverterTemplate import DataConverterTemplate
from Infrastructure.DataTypes.PathManager.PathManager import PathManager
from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats


class TraceConversionError(Exception):
    pass


class AutoTraceConverter:
    def __init__(self, path_manager: PathManager, source_format: InputOutputTraceFormats, target_format: InputOutputTraceFormats):
        self.source_format = source_format
        self.target_format = target_format
        self.path_manager = path_manager

    def _conversion_chain(self) -> List[DataConverterTemplate]:
        auto_conversion_mapping = AutoConversionMapping(self.path_manager, "DataConverters")
        converter_chain = []
        for converter_name, converter_class, source, target in auto_conversion_mapping.resolve_format(self.source_format, self.target_format):
            try:
                converter_chain.append((converter_class(converter_name, self.path_manager.get_path("path_to_project")), source, target))
            except Exception as e:
                raise TraceConversionError(f"AutoTraceConverter: Failed to initialize converter: {e}")
        return converter_chain

    @staticmethod
    def reachable(path_manager, source, target) -> Optional[InputOutputTraceFormats, InputOutputTraceFormats, int]:
        try:
            res = AutoConversionMapping(path_manager, "DataConverters").resolve_format(source, target)
            return source, target, len(res)
        except Exception():
            return None

    def convert(self, input_file: str, output_file: str, params) -> str:
        trace_input_path = self.path_manager.get_path("trace_input_path")
        intermediate_working_space = self.path_manager.get_path("intermediate_working_space")
        trace_output_path = self.path_manager.get_path("trace_output_path")

        input_path_file = f"{trace_input_path}/{input_file}"
        output_file_name = os.path.basename(output_file)
        output_path_file = f"{trace_output_path}/{output_file_name}"
        if self.source_format == self.target_format:
            shutil.copy(input_path_file, output_path_file)
            return output_path_file

        input_file_name = os.path.basename(input_file)
        intermediate_infile = f"{input_file_name}.in"
        intermediate_outfile = f"{output_file_name}.out"
        intermediate_in = f"{intermediate_working_space}/{intermediate_infile}"
        intermediate_out = f"{intermediate_working_space}/{intermediate_outfile}"

        shutil.copy(input_path_file, intermediate_in)
        for converter, source, target in self._conversion_chain():
            try:
                converter.auto_convert(
                    intermediate_working_space, intermediate_infile,
                    intermediate_working_space, intermediate_outfile,
                    source, target, params
                )
                shutil.copy(intermediate_out, intermediate_in)
            except Exception as e:
                raise TraceConversionError(f"AutoTraceConverter: Conversion failed in {converter.__class__.__name__} from {source} to {target}: {e}")
        shutil.copy(intermediate_in, output_path_file)
        return f"scratch/{output_file_name}"
