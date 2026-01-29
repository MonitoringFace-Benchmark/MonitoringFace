from pathlib import Path
from typing import List, Dict, Tuple

import importlib

from Infrastructure.Builders.ProcessorBuilder.DataConverters.DataConverterTemplate import DataConverterTemplate
from Infrastructure.DataTypes.PathManager.PathManager import PathManager
from Infrastructure.InputOutputFormats import InputOutputFormats


class TraceConversionError(Exception):
    pass


class AutoTraceConverter:
    def __init__(self, path_manager: PathManager, trace_format: InputOutputFormats, target_format: InputOutputFormats):
        self.trace_format = trace_format
        self.target_format = target_format
        self.path_manager = path_manager
        self.converter = self.convert()

    def convert(self):
        auto_conversion_mapping = AutoConversionMapping(self.path_manager)
        converter_name, converter_class = auto_conversion_mapping.resolve_format(self.trace_format, self.target_format)
        return converter_class(converter_name, self.path_manager.get_path("path_to_project"))


class AutoConversionMapping:
    def __init__(self, path_manager: PathManager):
        self.path_manager = path_manager
        self.mappings: Dict[Tuple[InputOutputFormats, InputOutputFormats], List[str]] = {}
        self._build_mapping()

    def _build_mapping(self):
        infra_path = self.path_manager.get_path("path_to_infra")
        if infra_path is None:
            raise ValueError(f"AutoConversionMapping: path_to_infra not found in PathManager")
        for (name_conv, _) in _discover_contract_names(infra_path):
            for (_from, _to) in _retrieve_module(name_conv).conversion_scheme():
                if (_from, _to) in self.mappings:
                    self.mappings[(_from, _to)].append(name_conv)
                else:
                    self.mappings[(_from, _to)] = [name_conv]

    def resolve_format(self, from_format: InputOutputFormats, to_format: InputOutputFormats) -> Tuple[str, DataConverterTemplate]:
        converter_names = self.mappings.get((from_format, to_format), None)
        if converter_names is None:
            raise TraceConversionError(f"AutoConversionMapping: No converter found for {from_format} to {to_format}")
        for converter_name in converter_names:
            try:
                converter = _retrieve_module(converter_name)
                return converter_name, converter
            except Exception as e:
                raise TraceConversionError(f"AutoConversionMapping: Failed to load converter: {e}")
        raise TraceConversionError(f"AutoConversionMapping: Failed to load converter")


def _discover_contract_names(path_to_infra_: str) -> List[str]:
    converters = []
    for item in Path(f"{path_to_infra_}/Builders/ProcessorBuilder/DataConverters").iterdir():
        if not item.is_dir() or item.name.startswith('_') or item.name == '__pycache__':
            continue
        for file in item.iterdir():
            if file.suffix == '.py' and 'Converter' in file.stem:
                converters.append((item.name, file.stem))
    return converters


def _retrieve_module(name):
    return getattr(importlib.import_module(f"Infrastructure.Builders.ProcessorBuilder.DataConverters.{name}.{name}"), name)


if __name__ == "__main__":
    from Infrastructure.DataTypes.PathManager.PathManager import PathManager
    pm = PathManager()
    pm.add_path("path_to_project", "/Users/krq770/PycharmProjects/MonitoringFace_curr")
    pm.add_path("path_to_infra", "/Users/krq770/PycharmProjects/MonitoringFace_curr/Infrastructure")
    atm = AutoTraceConverter(pm, InputOutputFormats.CSV, InputOutputFormats.OOO_CSV)
    atm.convert_setting()

