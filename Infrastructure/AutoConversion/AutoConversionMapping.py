import importlib
from pathlib import Path
from typing import List, Dict, TypeVar, Generic, Tuple

from Infrastructure.DataTypes.PathManager.PathManager import PathManager
F = TypeVar('F')
T = TypeVar('T')


class AutoConversionMapping(Generic[F, T]):
    def __init__(self, path_manager: PathManager, ttype: str):
        self.path_manager = path_manager
        self.ttype = ttype
        self.mappings: Dict[Tuple[F, F], List[str]] = {}
        self._build_mapping()

    def _build_mapping(self):
        infra_path = self.path_manager.get_path("path_to_infrastructure")
        if infra_path is None:
            raise ValueError(f"AutoConversionMapping: path_to_infra not found in PathManager")
        for (name_conv, _) in _discover_trace_converters(infra_path, self.ttype):
            for (_from, _to) in _retrieve_module(self.ttype, name_conv).conversion_scheme():
                if (_from, _to) in self.mappings:
                    self.mappings[(_from, _to)].append(name_conv)
                else:
                    self.mappings[(_from, _to)] = [name_conv]

    def resolve_format(self, from_format: F, to_format: F) -> List[Tuple[str, T]]:
        reachability_graph = AutoConversionReachabilityGraph(self.mappings)
        pipeline = []
        for (converter_name, (source, target)) in reachability_graph.find_path(from_format, to_format):
            try:
                pipeline.append((converter_name, _retrieve_module(self.ttype, converter_name), source, target))
            except Exception as e:
                raise ConversionErrorException(f"AutoConversionMapping: Failed to load converter: {e}")
        return pipeline


class Vertex:
    def __init__(self, value: F, edges: Tuple[F, List[str]]):
        self.value = value
        self.edges = list()
        target, tools = edges
        for tool in tools:
            self.edges.append((target, tool))

    def __repr__(self):
        return f"Vertex({self.value}, {self.edges})"

    def resolve_edges(self, target: F) -> List[str]:
        tools = []
        for (target_format, tool) in self.edges:
            if target_format == target:
                tools.append(tool)
        return tools

    def add_edges(self, target: F, converter: List[str]):
        for tool in converter:
            self.edges.append((target, tool))


class ConversionErrorException(Exception):
    pass


class AutoConversionReachabilityGraph:
    def __init__(self, mapping: Dict[Tuple[F, F], List[str]]):
        self.graph: Dict[F, Vertex] = dict()
        for ((source, target), converters) in mapping.items():
            if source in self.graph:
                self.graph[source].add_edges(target, converters)
            else:
                self.graph[source] = Vertex(source, (target, converters))
            if target not in self.graph:
                self.graph[target] = Vertex(target, (source, []))

    def find_path(self, source: F, target: F) -> List[str]:
        if source not in self.graph:
            raise ConversionErrorException(f"AutoConversionReachabilityGraph: Source Format {source} not in graph")
        if target not in self.graph:
            raise ConversionErrorException(f"AutoConversionReachabilityGraph: Target Format {target} not in graph")

        def bfs(graph, src, _target):
            visited = set()
            queue = [(src, [])]
            while queue:
                vertex, path = queue.pop(0)
                if vertex in visited:
                    continue
                visited.add(vertex)
                for (neighbor_value, tool) in graph[vertex].edges:
                    if neighbor_value == _target:
                        return path + [(tool, (vertex, _target))]
                    if neighbor_value not in visited:
                        queue.append((neighbor_value, path + [(tool, (vertex, neighbor_value))]))
            raise ConversionErrorException(f"AutoConversionReachabilityGraph: No path found from {source} to {target}")
        return bfs(self.graph, source, target)


def _discover_trace_converters(path_to_infra_: str, ttype: str) -> List[str]:
    converters = []
    for item in Path(f"{path_to_infra_}/Builders/ProcessorBuilder/{ttype}").iterdir():
        if not item.is_dir() or item.name.startswith('_') or item.name == '__pycache__':
            continue
        for file in item.iterdir():
            if file.suffix == '.py' and 'Converter' in file.stem:
                converters.append((item.name, file.stem))
    return converters


def _retrieve_module(ttype: str, name: str):
    return getattr(importlib.import_module(f"Infrastructure.Builders.ProcessorBuilder.{ttype}.{name}.{name}"), name)
