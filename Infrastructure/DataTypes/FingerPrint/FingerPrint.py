import hashlib
import json
from enum import Enum

from dataclasses import is_dataclass, asdict

from Infrastructure.Builders.ProcessorBuilder.DataGenerators.DataGeneratorTemplate import DataGeneratorTemplate
from Infrastructure.Builders.ProcessorBuilder.PolicyGenerators.PolicyGeneratorTemplate import PolicyGeneratorTemplate
from Infrastructure.DataTypes.Contracts.AbstractContract import AbstractContract


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
    elif isinstance(obj, AbstractContract):
        return {k: normalize(v) for k, v in obj.__dict__.items()}
    elif hasattr(obj, '__dict__') and not isinstance(obj, type):
        return {k: normalize(v) for k, v in obj.__dict__.items()}
    else:
        return obj


def data_class_to_finger_print(data_class_instance):
    normalized = normalize(data_class_instance)
    serialized = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
