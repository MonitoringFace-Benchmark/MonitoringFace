"""Zips the completeness claims of timelymon's claim_gen into a trace and,
with pacing on, prefixes every line with its replay due time for the driver's
`--format prefixed`.

claim_gen writes positional claims files, `pos<TAB>utter_ms<TAB>claim`: the
claim belongs after the first `pos` trace lines, and `utter_ms` is the
recorded time at which its rule settled it. The claims use this framework's
spelling (`>ELAPSED tp @ ts<`, `>WATERMARK tp<`). The trace's receipt-time
sidecar (`rx`) holds one time in ms per trace line, non-decreasing. With
pacing, a fact goes out as `<rx>\\t<line>` and a claim as `<utter_ms>\\t<claim>`;
the driver paces by the prefix (scaled by `speed`) and strips it, so the
monitor and the driver log see the plain lines. The claims were computed
offline on the recorded clocks, so every replay speed yields the same claims
at the same stream positions.
"""

from typing import Dict, Iterator, List, Optional, TextIO, Tuple

from Infrastructure.Builders.ProcessorBuilder.StreamProcessors.ClaimFamily import (
    claim_tp, watermark_tp)
from Infrastructure.Builders.ProcessorBuilder.StreamProcessors.StreamProcessorTemplate import (
    StreamProcessorException, StreamProcessorTemplate)


def claim_records(path: str) -> Iterator[Tuple[int, int, str]]:
    with open(path) as f:
        for number, raw in enumerate(f, 1):
            if raw.startswith("#") or not raw.strip():
                continue
            parts = raw.rstrip("\n").split("\t", 2)
            try:
                pos, utter = int(parts[0]), int(parts[1])
                claim = parts[2]
            except (IndexError, ValueError):
                raise StreamProcessorException(
                    f"ClaimZipper: malformed claims line {number}: {raw!r}") from None
            if claim_tp(claim) is None and watermark_tp(claim) is None:
                raise StreamProcessorException(
                    f"ClaimZipper: line {number} is neither >ELAPSED tp @ ts< nor >WATERMARK tp<: {claim!r}")
            yield pos, utter, claim


class ClaimZipper(StreamProcessorTemplate):
    buffering = False
    deterministic = True

    def setup(self, params: Dict) -> None:
        if "claims" not in params:
            raise StreamProcessorException(
                "ClaimZipper requires a 'claims' param (a claim_gen --claims-out file)")
        self.pacing = bool(params.get("pacing", True))
        rx_path = params.get("rx")
        if self.pacing and not rx_path:
            raise StreamProcessorException(
                "ClaimZipper with pacing requires an 'rx' param (the trace's receipt-time sidecar)")
        self._claims = claim_records(params["claims"])
        self._next: Optional[Tuple[int, int, str]] = next(self._claims, None)
        self._rx: Optional[TextIO] = open(rx_path) if self.pacing else None
        self.lines = 0
        self.claims = 0
        self.last_pos = 0
        self.last_due = 0

    def _due(self, due: int) -> int:
        if due < self.last_due:
            raise StreamProcessorException(
                f"ClaimZipper: due times decrease ({due} after {self.last_due} ms) at trace line "
                f"{self.lines + 1}; the trace must be in ingestion order")
        self.last_due = due
        return due

    def _claims_upto(self, pos: int) -> List[str]:
        out = []
        while self._next is not None and self._next[0] <= pos:
            p, utter, claim = self._next
            if p < self.last_pos:
                raise StreamProcessorException(
                    f"ClaimZipper: claim positions decrease ({p} after {self.last_pos})")
            self.last_pos = p
            # a claim is never paced before the line it follows
            out.append(f"{self._due(max(utter, self.last_due))}\t{claim}" if self.pacing else claim)
            self.claims += 1
            self._next = next(self._claims, None)
        return out

    def feed(self, line: str) -> List[str]:
        out = self._claims_upto(self.lines)
        if self.pacing:
            rx = self._rx.readline()
            if not rx.strip():
                raise StreamProcessorException(
                    f"ClaimZipper: the rx sidecar ends before trace line {self.lines + 1}")
            out.append(f"{self._due(int(rx))}\t{line}")
        else:
            out.append(line)
        self.lines += 1
        return out

    def flush(self) -> List[str]:
        out = self._claims_upto(self.lines)
        if self._next is not None:
            raise StreamProcessorException(
                f"ClaimZipper: a claim at position {self._next[0]} lies beyond the trace "
                f"({self.lines} lines): wrong claims file for this trace?")
        if self._rx is not None:
            if self._rx.readline().strip():
                raise StreamProcessorException(
                    f"ClaimZipper: the rx sidecar has more lines than the trace ({self.lines})")
            self._rx.close()
        return out

    def stats(self) -> Dict:
        return {"lines": self.lines, "claims": self.claims, "pacing": self.pacing}
