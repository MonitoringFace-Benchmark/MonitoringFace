"""Unbounded future operators for VeriMon on a finite trace.

VeriMon (and MonPoly) reject the future operators EVENTUALLY (or SOMETIMES),
ALWAYS, UNTIL and RELEASE with an unbounded interval, written `[a,*)` or left
out. On a finite trace they do not need one:
every later time point j of a time point i has ts(j) - ts(i) <= C, the trace's
timestamp span, so `[a,*)` and `[a,C]` select the same time points. VeriMon
closes the trace at the end of the log (a time point whose window reaches past
the last timestamp is decided as if no event follows), which is how an offline
monitor ends an unbounded future operator too. With C at least the span, the
bounded formula therefore gives the unbounded formula's verdicts on that trace.

NEXT is accepted with an unbounded interval and is left alone, as are bounded
intervals and the past operators.
"""

import math
import os
import re
from typing import Optional, Tuple

from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats
from Infrastructure.Provenance.Provenance import ConversionStep
from Infrastructure.constants import POLICY_KEY, TRACE_KEY, TRACE_TARGET_FORMAT

_OPERATOR = re.compile(r"\b(EVENTUALLY|SOMETIMES|ALWAYS|UNTIL|RELEASE)\b")
_INTERVAL = re.compile(r"(\s*)([\[(])\s*(\d+)\s*([a-z]*)\s*,\s*(\*|\d+\s*[a-z]*)\s*([\])])")
_TIME_POINT = re.compile(r"(?:^|;)\s*@\s*(\d+(?:\.\d+)?)", re.M)
_UNIT_SECONDS = {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400}


def bound_unbounded_future(formula: str, horizon: int) -> Tuple[str, int]:
    """Replace every unbounded future interval (EVENTUALLY, SOMETIMES, ALWAYS,
    UNTIL, RELEASE) by one ending at `horizon` (at least its lower bound). Returns the new formula and
    the number of operators bounded."""
    out = []
    pos = 0
    bounded = 0
    for operator in _OPERATOR.finditer(formula):
        if operator.start() < pos:
            continue
        out.append(formula[pos:operator.end()])
        pos = operator.end()
        interval = _INTERVAL.match(formula, pos)
        if interval is None:
            out.append(f"[0,{horizon}]")
            bounded += 1
        elif interval.group(5) == "*":
            space, left, lower, unit = interval.group(1, 2, 3, 4)
            if unit not in _UNIT_SECONDS:
                raise ValueError(f"Unknown time unit '{unit}' in the interval of {operator.group(1)}")
            upper = max(horizon, int(lower) * _UNIT_SECONDS[unit])
            out.append(f"{space}{left}{lower}{unit},{upper}]")
            pos = interval.end()
            bounded += 1
    out.append(formula[pos:])
    return "".join(out), bounded


def timestamp_span(monpoly_log: str) -> Optional[int]:
    """Largest minus smallest timestamp of a MonPoly log, rounded up; None for a
    log without time points."""
    lowest = highest = None
    with open(monpoly_log, "r") as log:
        for line in log:
            for time_point in _TIME_POINT.finditer(line):
                ts = float(time_point.group(1))
                lowest = ts if lowest is None else min(lowest, ts)
                highest = ts if highest is None else max(highest, ts)
    return None if lowest is None else math.ceil(highest - lowest)


def bound_policy_to_trace(params, path_to_folder: str) -> Optional[ConversionStep]:
    """After a MonPoly-family tool's preprocessing: when its policy has an
    unbounded future operator and its trace is a MonPoly log, write the policy
    bounded by the trace's timestamp span to the scratch folder and point the
    tool at it. Returns the provenance step, or None when nothing changed."""
    if params.get(TRACE_TARGET_FORMAT) not in (InputOutputTraceFormats.MONPOLY,
                                               InputOutputTraceFormats.MONPOLY_LINEAR):
        return None
    policy_file = params[POLICY_KEY]
    with open(os.path.join(path_to_folder, policy_file), "r") as policy:
        formula = policy.read()
    if not _OPERATOR.search(formula):
        return None
    horizon = timestamp_span(os.path.join(path_to_folder, params[TRACE_KEY])) or 0
    bounded_formula, bounded = bound_unbounded_future(formula, horizon)
    if bounded == 0:
        return None
    os.makedirs(os.path.join(path_to_folder, "scratch"), exist_ok=True)
    bounded_file = f"scratch/bounded_{os.path.basename(policy_file)}"
    with open(os.path.join(path_to_folder, bounded_file), "w") as policy:
        policy.write(bounded_formula)
    params[POLICY_KEY] = bounded_file
    return ConversionStep(
        converter="BoundUnboundedFuture", source_format="mfotl", target_format="mfotl",
        command=None, cmd_params=None, params={"horizon": horizon, "bounded_operators": bounded}
    )
