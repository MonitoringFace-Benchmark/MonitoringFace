import os
import re
from typing import Dict, AnyStr, Any, Tuple, List, Optional

from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats
from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats
from Infrastructure.Builders.ToolBuilder.ToolImageManager import AbstractToolImageManager
from Infrastructure.DataTypes.PathManager.PathManager import PathManager
from Infrastructure.DataTypes.Verification.OutputStructures.AbstractOutputStrucutre import AbstractOutputStructure
from Infrastructure.DataTypes.Verification.OutputStructures.Structures.OooVerdicts import OooVerdicts
from Infrastructure.DataTypes.Verification.OutputStructures.SubTypes.VariableOrder import VariableOrder, \
    DefaultVariableOrder
from Infrastructure.Monitors.BaseMonitorTemplate import BaseMonitorTemplate, OfflineRunnable, OnlineRunnable
from Infrastructure.constants import POLICY_KEY, TRACE_KEY, SIGNATURE_KEY, FOLDER_KEY, OOO_FREE_VARIABLES


class OOOMon(BaseMonitorTemplate, OfflineRunnable, OnlineRunnable):
    """The Isabelle-verified out-of-order reference monitor (formalized_streaming_monitor).

    Everything between a parsed token and a printed verdict runs OCaml code
    exported from the verified OOOMonitor session; only the parsers and
    printers are unverified glue.  Policies are fragment-direct s-expressions
    (format "ooo-fragment"); traces are the TimelyMon CSV wire format,
    in-order or out-of-order, with optional time-point watermarks.
    """

    def __init__(self, image: AbstractToolImageManager, name, params: Dict[AnyStr, Any]):
        super().__init__(image, name, params)

    def preprocessing_data(
            self, path_to_folder: AnyStr, data_file: AnyStr,
            trace_source: InputOutputTraceFormats, path_manager: PathManager
    ):
        raise NotImplementedError("OOOMon does not support non-automatic preprocessing for data")

    def preprocessing_policy(self, path_to_folder: AnyStr, policy_file: AnyStr, signature_file: AnyStr,
                             policy_source: InputOutputPolicyFormats, path_manager: PathManager):
        raise NotImplementedError("OOOMon does not support non-automatic preprocessing for policies")

    def construct_offline_command(self) -> Tuple[List[str], Optional[str]]:
        cmd = ["-formula", str(self.params[POLICY_KEY]),
               "-log", str(self.params[TRACE_KEY]),
               "-format", "timelymon"]
        if not self.params.get("ignore_signature", False):
            cmd += ["-sig", str(self.params[SIGNATURE_KEY])]
        if self.params.get("no_claims", False):
            cmd += ["-no-claims"]
        return cmd, None

    def post_processing_offline(self, stdout_input: AnyStr) -> AbstractOutputStructure:
        trace = os.path.join(str(self.params[FOLDER_KEY]), str(self.params[TRACE_KEY]))
        return parse_output_structure(stdout_input, self._variable_order(), last_trace_time_point(trace))

    def construct_online_command(self) -> Tuple[List[str], Optional[str]]:
        cmd = ["-formula", "additional/policy.policy", "-format", "timelymon", "-ack"]
        if not self.params.get("ignore_signature", False):
            cmd += ["-sig", "additional/signature.sig"]
        if self.params.get("no_claims", False):
            cmd += ["-no-claims"]
        return cmd, None

    @staticmethod
    def latency_marker() -> Optional[str]:
        return None

    def post_processing_online(self, stdout_input: AnyStr) -> AbstractOutputStructure:
        pass

    def _variable_order(self):
        cmd = ["-formula", str(self.params[POLICY_KEY]), "-columns"]
        logs, code = self.image.run_offline(self.params[FOLDER_KEY], cmd, measure=False)
        order = parse_variable_order_ooomon(logs) if code == 0 else []
        order = restore_variable_names(order, self.params.get(OOO_FREE_VARIABLES))
        return VariableOrder(order) if order else DefaultVariableOrder()

    @staticmethod
    def supported_policy_formats() -> List[InputOutputPolicyFormats]:
        return [InputOutputPolicyFormats.OOO_FRAGMENT]

    @staticmethod
    def supported_trace_formats() -> List[InputOutputTraceFormats]:
        return [InputOutputTraceFormats.CSV, InputOutputTraceFormats.OOO_CSV]


def parse_variable_order_ooomon(text: AnyStr) -> List[str]:
    """`ooomon -formula F -columns` prints exactly one line: `# columns: x0 x1 ...`."""
    match = re.search(r"#\s*columns:\s*(.*)", text)
    if not match:
        return []
    return [v for v in match.group(1).split() if v]


def restore_variable_names(columns: List[str], free_variables: Optional[List[str]]) -> List[str]:
    """The fragment converter renames the MFOTL free variables to x0, x1, ...
    (sorted by natural name order), so `-columns` reports those and not the
    names the oracle uses. Assignments compare by (name, value), so the
    verdicts would never match the oracle's: map x{i} back to the i-th name
    the converter recorded. Columns are left as they are when the converter
    did not run (a policy handed over in fragment format) or a column is not
    of the x{i} shape."""
    if not free_variables:
        return columns
    restored = []
    for column in columns:
        match = re.fullmatch(r"x(\d+)", column)
        index = int(match.group(1)) if match else None
        if index is not None and index < len(free_variables):
            restored.append(free_variables[index])
        else:
            restored.append(column)
    return restored


DROPPED_BEYOND_TRACE_END = "beyond_trace_end"
DROPPED_DUPLICATES = "duplicates"

_VERDICT_LINE = re.compile(r'^@(\d+)\s*\((.*)\)\s*$')
# time-points a TimelyMon-format trace names: event `tp=` fields and point
# claims; a watermark names the point AFTER its prefix, so it does not count
_TRACE_TIME_POINT = re.compile(r'(?:\btp\s*=\s*|>ELAPSED\s+)(\d+)')


def parse_output_structure(input_val: AnyStr, variable_ordering,
                           last_time_point: Optional[int] = None) -> AbstractOutputStructure:
    """Parse `@tp (v1,v2,...)` verdict lines; `# columns` headers and
    `!complete` claims are metadata, not verdicts.

    Two kinds of lines are dropped, and counted under `dropped`:

    `beyond_trace_end`: OOOMon reasons over an infinite trace. At end of file
    the frontend claims every time-point it has seen complete, and the
    verified core then fires the verdicts that no longer depend on anything
    unknown. A `PREV [0,*]` verdict for the time-point AFTER the last one is
    such a verdict (it reads the completed last time-point, and the unbounded
    interval is decided without that next timestamp), so the tool reports
    time-points the finite trace does not contain, one per nested PREV. Every
    verdict above the trace's last time-point (`last_time_point`, from the
    trace the tool read: last_trace_time_point) is dropped. OOOMon's own
    `!complete` claims do not mark the trace end: they cover the time-points
    whose verdict set is final, and under a future operator that stops below
    the end (its windows reach past it), while the verdicts emitted there are
    verdicts of the trace. Without `last_time_point` nothing is dropped.

    `duplicates`: the core re-emits a small share of verdicts (the same tuple
    at the same time-point, twice, inside the streaming output). The oracle
    comparison is on sorted lists, so a repeat fails an otherwise identical
    verdict set; only the first emission is kept."""
    verdicts = OooVerdicts(variable_order=variable_ordering)
    verdicts.dropped[DROPPED_BEYOND_TRACE_END] = 0
    verdicts.dropped[DROPPED_DUPLICATES] = 0
    if input_val is None or input_val.strip() == "":
        return verdicts

    seen = set()
    for line in input_val.strip().split("\n"):
        match = _VERDICT_LINE.match(line.strip())
        if not match:
            continue
        tp = int(match.group(1))
        if last_time_point is not None and tp > last_time_point:
            verdicts.dropped[DROPPED_BEYOND_TRACE_END] += 1
            continue
        values = tuple(_strip_quotes(v) for v in _split_top_level(match.group(2)))
        if (tp, values) in seen:
            verdicts.dropped[DROPPED_DUPLICATES] += 1
            continue
        seen.add((tp, values))
        values = list(values)
        verdicts.insert([values] if values else [[]], tp, None)
    return verdicts


def last_trace_time_point(path: str) -> Optional[int]:
    """Highest time-point the trace OOOMon read names (events and point
    claims); None, with a warning, when the file cannot be read or names
    none, and then no verdict is dropped as beyond the trace end."""
    highest = None
    try:
        with open(path) as f:
            for line in f:
                for match in _TRACE_TIME_POINT.finditer(line):
                    tp = int(match.group(1))
                    highest = tp if highest is None or tp > highest else highest
    except OSError as e:
        print(f"OOOMon: cannot read the trace for its last time-point ({e}); "
              f"verdicts past the trace end are kept")
        return None
    if highest is None:
        print(f"OOOMon: {path} names no time-point; verdicts past the trace end are kept")
    return highest


def _split_top_level(s: str) -> List[str]:
    """Split a verdict tuple on commas, respecting double-quoted strings."""
    out, buf, in_q = [], [], False
    for c in s:
        if c == '"':
            in_q = not in_q
            buf.append(c)
        elif c == ',' and not in_q:
            out.append("".join(buf).strip())
            buf = []
        else:
            buf.append(c)
    tail = "".join(buf).strip()
    if tail or out:
        out.append(tail)
    return [v for v in out if v != ""]


def _strip_quotes(v: str) -> str:
    if len(v) >= 2 and v[0] == '"' and v[-1] == '"':
        return v[1:-1]
    return v
