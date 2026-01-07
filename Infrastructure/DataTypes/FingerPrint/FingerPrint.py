import hashlib
import sys
from enum import Enum

import yaml
from dataclasses import is_dataclass, asdict

from Infrastructure.Builders.ProcessorBuilder.DataGenerators.DataGeneratorTemplate import DataGeneratorTemplate
from Infrastructure.Builders.ProcessorBuilder.PolicyGenerators.PolicyGeneratorTemplate import PolicyGeneratorTemplate


def normalize(obj):
    if is_dataclass(obj):
        return {k: normalize(v) for k, v in asdict(obj).items()}
    elif isinstance(obj, Enum):
        return obj.name
    elif isinstance(obj, list):
        return [normalize(x) for x in obj]
    elif isinstance(obj, dict):
        return {k: normalize(v) for k, v in obj.items()}
    elif isinstance(obj, DataGeneratorTemplate):
        return f"{obj.__class__.__name__}"
    elif isinstance(obj, PolicyGeneratorTemplate):
        return f"{obj.__class__.__name__}"
    else:
        return obj


def data_class_to_finger_print(data_class_instance):
    if not is_dataclass(data_class_instance):
        raise NotImplemented("Not a dataclass")
    serialized = yaml.safe_dump(normalize(data_class_instance), sort_keys=True, default_flow_style=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
