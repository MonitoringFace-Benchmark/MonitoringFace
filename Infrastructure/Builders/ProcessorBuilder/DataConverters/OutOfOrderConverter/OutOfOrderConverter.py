import random
from enum import Enum
from typing import AnyStr, List
import re

from Infrastructure.Builders.ProcessorBuilder.DataConverters.DataConverterTemplate import DataConverterTemplate

DEFAULT_SEED = 42
MAX_DISTANCE = 5
PERCENTAGE_DELAYED = 0.2


class Modes(Enum):
    Reverse = 1
    Delayed = 2
    OutOfOrderTimePoints = 3
    OutOfOrderEvents = 4


def str_to_mode(mode_str: AnyStr) -> Modes:
    mode_str = mode_str.lower()
    if mode_str == "reverse":
        return Modes.Reverse
    elif mode_str == "delayed":
        return Modes.Delayed
    elif mode_str == "oootps":
        return Modes.OutOfOrderTimePoints
    elif mode_str == "oooevents":
        return Modes.OutOfOrderEvents
    else:
        return Modes.Delayed


def group_by_tp(events: List) -> List[List]:
    tp_groups = {}
    for event in events:
        tp = extract_tp_value(event)
        if tp not in tp_groups:
            tp_groups[tp] = []
        tp_groups[tp].append(event)
    return [tp_groups[tp] for tp in sorted(tp_groups.keys())]


def extract_watermark_value(watermark: str) -> int:
    match = re.search(r'>WATERMARK\s+(\d+)<', watermark)
    if match:
        return int(match.group(1))
    raise ValueError(f"Invalid watermark format: {watermark}")


def extract_tp_value(event: str) -> int:
    match = re.search(r'tp=(\d+)', event)
    if match:
        return int(match.group(1))
    raise ValueError(f"No tp value found in event: {event}")


def random_subset(items: List, seed: int) -> List:
    if not items:
        return []
    rng = random.Random(seed)
    k = rng.randint(1, len(items))
    return rng.sample(items, k)


def interleave_with_watermarks(events: List[str], watermarks: List[str]) -> List[str]:
    if not watermarks:
        return events

    result = list(events)
    sorted_watermarks = sorted(watermarks, key=extract_watermark_value)

    for watermark in sorted_watermarks:
        wm_value = extract_watermark_value(watermark)
        earliest_valid_index = 0
        for i, event in enumerate(result):
            if not event.startswith(">W"):
                tp = extract_tp_value(event)
                if tp <= wm_value:
                    earliest_valid_index = i + 1
        result.insert(earliest_valid_index, watermark)
    return result


def ooo_events_mode(events: List, watermarks: List, seed: int) -> List:
    random.Random(seed).shuffle(events)
    return interleave_with_watermarks(events, random_subset(watermarks, seed))


def oootps_mode(events: List, watermarks: List, seed: int) -> List:
    groups = group_by_tp(events)
    random.Random(seed).shuffle(groups)
    events = [event for group in groups for event in group]
    return interleave_with_watermarks(events, random_subset(watermarks, seed))


def delayed_mode(events: List, watermarks: List, seed: int, max_distance: int, percentage_delayed: float) -> List:
    rng = random.Random(seed)
    segs = group_by_tp(events)

    moved_elems = []
    for org_index, seg in enumerate(segs):
        percentage = rng.uniform(0.0, percentage_delayed)
        max_dist = rng.randint(0, max_distance)
        elements_to_sample = round(len(seg) * (percentage / 100.0))

        sampled = []
        for _ in range(elements_to_sample):
            if seg:
                index = rng.randint(0, len(seg) - 1)
                sampled.append(seg.pop(index))

        moved_elems.append((sampled, org_index + max_dist))

    offset = 0
    for delayed_seg, dist in moved_elems:
        new_index = dist + offset
        offset += 1
        if new_index >= len(segs):
            segs.append(delayed_seg)
        else:
            segs.insert(new_index, delayed_seg)

    events = [event for group in segs for event in group]
    return interleave_with_watermarks(events, random_subset(watermarks, seed))


class OutOfOrderConverter(DataConverterTemplate):
    def __init__(self, name, path_to_project):
        pass

    def convert(self, path_to_folder: AnyStr, data_file: AnyStr, tool: AnyStr, name: AnyStr, dest: AnyStr, params):
        mode = str_to_mode(params["mode"])
        seed = params.get("seed", DEFAULT_SEED)
        max_distance = params.get("max_distance", MAX_DISTANCE)
        percentage_delayed = params.get("percentage_delayed", PERCENTAGE_DELAYED)

        with open(f"{path_to_folder}/{data_file}", "r") as f:
            lines = f.readlines()

        events, watermarks = [], []
        for line in lines:
            if line.startswith(">W"):
                watermarks.append(line)
            else:
                events.append(line)

        if mode == Modes.Reverse:
            result = reversed(events)
        elif mode == Modes.Delayed:
            result = delayed_mode(events, watermarks, seed, max_distance, percentage_delayed)
        elif mode == Modes.OutOfOrderTimePoints:
            result = oootps_mode(events, watermarks, seed)
        elif mode == Modes.OutOfOrderEvents:
            result = ooo_events_mode(events, watermarks, seed)
        else:
            result = lines

        with open(f"{dest}/{name}.{tool}", "w") as f:
            f.write("\n".join(result))
