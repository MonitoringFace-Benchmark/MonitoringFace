import hashlib
from enum import Enum

import yaml
from dataclasses import is_dataclass, asdict


def normalize(obj):
    if is_dataclass(obj):
        return {k: normalize(v) for k, v in asdict(obj).items()}
    elif isinstance(obj, Enum):
        return obj.name
    elif isinstance(obj, list):
        return [normalize(x) for x in obj]
    elif isinstance(obj, dict):
        return {k: normalize(v) for k, v in obj.items()}
    else:
        return obj


def data_class_to_finger_print(data_class_instance):
    if not is_dataclass(data_class_instance):
        raise NotImplemented("Not a dataclass")
    serialized = yaml.safe_dump(normalize(data_class_instance), sort_keys=True, default_flow_style=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
