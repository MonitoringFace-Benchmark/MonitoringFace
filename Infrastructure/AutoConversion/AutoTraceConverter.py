import shutil
from pathlib import Path
from typing import List, Dict, Tuple

import importlib

from Infrastructure.Builders.ProcessorBuilder.DataConverters.DataConverterTemplate import DataConverterTemplate
from Infrastructure.DataTypes.PathManager.PathManager import PathManager
from Infrastructure.InputOutputFormats import InputOutputFormats


class TraceConversionError(Exception):
    pass


class AutoTraceConverter:
    def __init__(self, path_manager: PathManager, source_format: InputOutputFormats, target_format: InputOutputFormats):
        self.source_format = source_format
        self.target_format = target_format
        self.path_manager = path_manager

    def _conversion_chain(self) -> List[DataConverterTemplate]:
        auto_conversion_mapping = AutoConversionMapping(self.path_manager)
        converter_chain = []
        for converter_name, converter_class, source, target in auto_conversion_mapping.resolve_format(self.source_format, self.target_format):
            try:
                converter_chain.append((converter_class(converter_name, self.path_manager.get_path("path_to_project")), source, target))
            except Exception as e:
                raise TraceConversionError(f"AutoTraceConverter: Failed to initialize converter: {e}")
        return converter_chain

    def convert(
            self, trace_input_path: str, input_file: str,
            intermediate_working_space: str,
            trace_output_path: str, output_file: str, params
    ):
        intermediate_infile = f"{input_file}.in"
        intermediate_outfile = f"{output_file}.out"
        intermediate_in = f"{intermediate_working_space}/{intermediate_infile}"
        intermediate_out = f"{intermediate_working_space}/{intermediate_outfile}"

        shutil.copy(f"{trace_input_path}/{input_file}", intermediate_in)
        for converter, source, target in self._conversion_chain():
            converter.convert(
                intermediate_working_space, intermediate_infile,
                intermediate_working_space, intermediate_outfile,
                source, target, params
            )
            shutil.copy(intermediate_out, intermediate_in)
        shutil.copy(intermediate_in, f"{trace_output_path}/{output_file}")


class AutoConversionMapping:
    def __init__(self, path_manager: PathManager):
        self.path_manager = path_manager
        self.mappings: Dict[Tuple[InputOutputFormats, InputOutputFormats], List[str]] = {}
        self._build_mapping()

    def _build_mapping(self):
        infra_path = self.path_manager.get_path("path_to_infra")
        if infra_path is None:
            raise ValueError(f"AutoConversionMapping: path_to_infra not found in PathManager")
        for (name_conv, _) in _discover_trace_converters(infra_path):
            for (_from, _to) in _retrieve_module(name_conv).conversion_scheme():
                if (_from, _to) in self.mappings:
                    self.mappings[(_from, _to)].append(name_conv)
                else:
                    self.mappings[(_from, _to)] = [name_conv]

    def resolve_format(self, from_format: InputOutputFormats, to_format: InputOutputFormats) -> List[Tuple[str, DataConverterTemplate]]:
        reachability_graph = AutoConversionReachabilityGraph(self.mappings)
        pipeline = []
        for (converter_name, (source, target)) in reachability_graph.find_path(from_format, to_format):
            try:
                pipeline.append((converter_name, _retrieve_module(converter_name), source, target))
            except Exception as e:
                raise TraceConversionError(f"AutoConversionMapping: Failed to load converter: {e}")
        return pipeline


class Vertex:
    def __init__(self, value: InputOutputFormats, edges: Tuple[InputOutputFormats, List[str]]):
        self.value = value
        self.edges = list()
        target, tools = edges
        for tool in tools:
            self.edges.append((target, tool))

    def __repr__(self):
        return f"Vertex({self.value}, {self.edges})"

    def resolve_edges(self, target: InputOutputFormats) -> List[str]:
        tools = []
        for (target_format, tool) in self.edges:
            if target_format == target:
                tools.append(tool)
        return tools

    def add_edges(self, target: InputOutputFormats, converter: List[str]):
        for tool in converter:
            self.edges.append((target, tool))


class AutoConversionReachabilityGraph:
    def __init__(self, mapping: Dict[Tuple[InputOutputFormats, InputOutputFormats], List[str]]):
        self.graph: Dict[InputOutputFormats, Vertex] = dict()
        for ((source, target), converters) in mapping.items():
            if source in self.graph:
                self.graph[source].add_edges(target, converters)
            else:
                self.graph[source] = Vertex(source, (target, converters))
            if target not in self.graph:
                self.graph[target] = Vertex(target, (source, []))

    def find_path(self, source: InputOutputFormats, target: InputOutputFormats) -> List[str]:
        if source not in self.graph:
            raise TraceConversionError(f"AutoConversionReachabilityGraph: Source Format {source} not in graph")
        if target not in self.graph:
            raise TraceConversionError(f"AutoConversionReachabilityGraph: Target Format {target} not in graph")

        def _dfs(graph, vertex, _target, _visited, _path) -> List[str]:
            src = vertex.value
            _visited.add(src)
            for (neighbor_value, tool) in vertex.edges:
                if neighbor_value == _target:
                    _path.insert(0, (tool, (src, target)))
                    return _path
                if neighbor_value not in _visited:
                    if neighbor_value not in self.graph:
                        continue
                    result = _dfs(graph, graph.get(neighbor_value), _target, _visited, _path)
                    if result:
                        _path.insert(0, (tool, (src, neighbor_value)))
                        return _path
            raise TraceConversionError(f"AutoConversionReachabilityGraph: No path found from {source} to {target}")
        return _dfs(self.graph, self.graph[source], target, set(), [])


def _discover_trace_converters(path_to_infra_: str) -> List[str]:
    converters = []
    for item in Path(f"{path_to_infra_}/Builders/ProcessorBuilder/DataConverters").iterdir():
        if not item.is_dir() or item.name.startswith('_') or item.name == '__pycache__':
            continue
        for file in item.iterdir():
            if file.suffix == '.py' and 'Converter' in file.stem:
                converters.append((item.name, file.stem))
    return converters


def _retrieve_module(name: str):
    return getattr(importlib.import_module(f"Infrastructure.Builders.ProcessorBuilder.DataConverters.{name}.{name}"), name)


if __name__ == "__main__":
    from Infrastructure.DataTypes.PathManager.PathManager import PathManager
    pm = PathManager()
    pm.add_path("path_to_project", "/Users/krq770/PycharmProjects/MonitoringFace_curr")
    pm.add_path("path_to_infra", "/Users/krq770/PycharmProjects/MonitoringFace_curr/Infrastructure")
    mapping = {
        (InputOutputFormats.OOO_CSV, InputOutputFormats.CSV): ["OrderRestorerConverter"],
        (InputOutputFormats.CSV, InputOutputFormats.MONPOLY): ["MonpolyConverter"],
    }
    ag = AutoConversionReachabilityGraph(mapping)
    x = ag.find_path(InputOutputFormats.OOO_CSV, InputOutputFormats.MONPOLY)
    print(x)

