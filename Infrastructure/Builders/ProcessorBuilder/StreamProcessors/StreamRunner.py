import os
from typing import Dict, List, Optional, Tuple

from Infrastructure.Builders.ProcessorBuilder.StreamProcessors.StreamProcessorTemplate import (
    StreamProcessorException, load_stream_processor)
from Infrastructure.Provenance.Provenance import ConversionStep, framework_commit

_COMMIT_CACHE: Dict[str, Optional[str]] = {}


def _cached_framework_commit(path_to_project: Optional[str]) -> Optional[str]:
    if not path_to_project:
        return None
    if path_to_project not in _COMMIT_CACHE:
        _COMMIT_CACHE[path_to_project] = framework_commit(path_to_project)
    return _COMMIT_CACHE[path_to_project]


def run_stage(processor, lines: List[str]) -> Tuple[List[str], Dict]:
    consumed = 0
    released = 0
    out: List[str] = []
    for line in lines:
        produced = processor.feed(line)
        consumed += 1
        released += len(produced)
        out.extend(produced)
    produced = processor.flush()
    released += len(produced)
    out.extend(produced)
    counters = {"consumed": consumed, "released": released,
                "dropped": getattr(processor, "dropped", 0) or 0}
    return out, counters


def apply_stream_pipeline(
        spec: List[Dict], input_path: str, output_path: str,
        source_format: str, path_to_project: Optional[str] = None
) -> List[ConversionStep]:
    with open(input_path, "r") as f:
        lines = f.read().splitlines()

    commit = _cached_framework_commit(path_to_project)
    steps: List[ConversionStep] = []
    for entry in spec:
        identifier = entry["identifier"]
        params = entry.get("params") or {}
        processor = load_stream_processor(identifier)(identifier)
        try:
            processor.setup(params)
            lines, counters = run_stage(processor, lines)
        except StreamProcessorException:
            raise
        except Exception as e:
            raise StreamProcessorException(
                f"stream processor {identifier} failed: {e}") from e
        steps.append(ConversionStep(
            converter=identifier, source_format=source_format,
            target_format=source_format, command=None, cmd_params=None,
            image=None, image_version=commit,
            params=dict(params), stats={**counters, **processor.stats()},
        ))

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        for line in lines:
            f.write(line + "\n")
    return steps
