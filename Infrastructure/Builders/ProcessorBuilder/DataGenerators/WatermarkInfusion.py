"""Watermarks for generated CSV traces (`watermarks: true` in a data setup).

The generators print their events time point by time point, in order.
`infuse_watermarks` adds one watermark per time point the way TimelyMon's own
trace tool does (`infuse_watermarks` in src/tools/shared_functions.rs) and as
its harness traces are laid out: when the next time point starts, it writes
`>WATERMARK tp<` for the time point tp that just ended. TimelyMon finalizes
the time points strictly below a watermark, so such a line settles the time
point before tp; the last time point is settled by the end of the input.
"""


def parse_tp(line: str) -> int:
    return int(line.split(",")[1].split("=")[1])


def infuse_watermarks(trace: str) -> str:
    lines = []
    current = None
    for line in trace.strip().split("\n"):
        if not line:
            continue
        tp = parse_tp(line)
        if current is not None and tp != current:
            lines.append(f">WATERMARK {current}<")
        current = tp
        lines.append(line)
    return "\n".join(lines)
