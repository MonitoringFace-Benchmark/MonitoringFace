from typing import Dict, List, Optional

from Infrastructure.Builders.ProcessorBuilder.StreamProcessors.ClaimFamily import (
    bridge_parts, claim_parts, extract_tp, watermark_tp)
from Infrastructure.Builders.ProcessorBuilder.StreamProcessors.StreamProcessorTemplate import (
    StreamProcessorException, StreamProcessorTemplate)


class Sorter(StreamProcessorTemplate):
    """Serialization adapter for in-order, prefix-based monitors: buffers
    events per time-point, absorbs completeness claims, and releases exactly
    the maximal contiguous run of complete time-points at the frontier. The
    disorderer's placement invariant (claim strictly after the tp's last
    event) guarantees every released tp is fully in hand.

    Canonical csv events are released as-is, one line per event. Bridge
    events (`@tp @ts atom(args)`) are released as one MonPoly-readable block
    per time-point, `@ts atom1 atom2 ...`, the @tp annotation consumed; an
    empty claimed time-point becomes a bare `@ts` block carrying the last
    released timestamp, keeping MonPoly's positional tp indexing aligned."""

    buffering = True
    deterministic = True

    def setup(self, params: Dict) -> None:
        self.frontier = int(params.get("base_tp", 0))
        self.stream_format: Optional[str] = None
        self.pending_empty: List[int] = []
        self.buffer: Dict[int, List[tuple]] = {}
        self.tp_ts: Dict[int, int] = {}
        self.last_released_ts = 0
        self.claims = set()
        self.index = 0
        self.dropped = 0
        self.last_origins: Optional[List[int]] = None
        self.claims_seen = 0
        self.releases = 0
        self.max_release_batch = 0
        self.peak_buffer_events = 0
        self.peak_open_timepoints = 0
        self.released_unclaimed = 0
        self.buffered_events = 0

    def feed(self, line: str) -> List[str]:
        self.index += 1
        claim = claim_parts(line)
        watermark = watermark_tp(line)
        if claim is not None:
            tp, ts = claim
            if tp in self.tp_ts and self.tp_ts[tp] != ts:
                raise StreamProcessorException(
                    f"Sorter: claim timestamp {ts} for tp {tp} contradicts "
                    f"the events' timestamp {self.tp_ts[tp]}")
            self.tp_ts.setdefault(tp, ts)
            self.claims_seen += 1
            self.dropped += 1
            self.claims.add(tp)
            return self._advance()
        if watermark is not None:
            self.claims_seen += 1
            self.dropped += 1
            self.claims.update(range(self.frontier, watermark))
            return self._advance()

        bridge = bridge_parts(line)
        line_format = "bridge" if bridge is not None else "csv"
        if self.stream_format is None:
            self.stream_format = line_format
        elif self.stream_format != line_format:
            raise StreamProcessorException(
                f"Sorter: mixed stream formats, saw {line_format} line {line!r} "
                f"in a {self.stream_format} stream")

        if bridge is not None:
            tp, ts, atom = bridge
            if tp in self.tp_ts and self.tp_ts[tp] != ts:
                raise StreamProcessorException(
                    f"Sorter: inconsistent timestamps for tp {tp}: "
                    f"{self.tp_ts[tp]} vs {ts}")
            self.tp_ts.setdefault(tp, ts)
            payload = atom
        else:
            tp = extract_tp(line)
            payload = line

        if tp < self.frontier or tp in self.claims:
            raise StreamProcessorException(
                f"Sorter: unsound stream, event of tp {tp} arrived after its "
                f"completeness claim (frontier {self.frontier})")
        self.buffer.setdefault(tp, []).append((self.index, payload))
        self.buffered_events += 1
        self.peak_buffer_events = max(self.peak_buffer_events, self.buffered_events)
        self.peak_open_timepoints = max(self.peak_open_timepoints, len(self.buffer))
        self.last_origins = None
        return []

    def _render(self, tps: List[int]) -> tuple:
        lines: List[str] = []
        origins: List[int] = []
        events = 0
        if self.stream_format == "bridge" and self.pending_empty:
            lines.extend(f"@{ts}" for ts in self.pending_empty)
            self.pending_empty = []
        for tp in tps:
            entries = self.buffer.pop(tp, [])
            events += len(entries)
            origins.extend(index for index, _ in entries)
            if self.stream_format == "bridge":
                ts = self.tp_ts.pop(tp, self.last_released_ts)
                self.last_released_ts = ts
                if entries:
                    lines.append(f"@{ts} " + " ".join(atom for _, atom in entries))
                    self.dropped += len(entries) - 1
                else:
                    lines.append(f"@{ts}")
            elif self.stream_format is None and not entries:
                # claimed empty tp before the first event: the format is not
                # known yet, so a bridge placeholder may still be owed
                self.pending_empty.append(self.tp_ts.get(tp, self.last_released_ts))
            else:
                lines.extend(payload for _, payload in entries)
        return lines, origins, events

    def _advance(self) -> List[str]:
        run: List[int] = []
        while self.frontier in self.claims:
            run.append(self.frontier)
            self.claims.discard(self.frontier)
            self.frontier += 1
        if not run:
            self.last_origins = None
            return []
        lines, origins, events = self._render(run)
        if not lines:
            self.last_origins = None
            return []
        self.buffered_events -= events
        self.releases += 1
        self.max_release_batch = max(self.max_release_batch, events)
        self.last_origins = origins
        return lines

    def flush(self) -> List[str]:
        remaining = sorted(self.buffer)
        lines, origins, events = self._render(remaining)
        self.buffered_events = 0
        if not lines:
            self.last_origins = None
            return []
        self.releases += 1
        self.released_unclaimed += events
        self.max_release_batch = max(self.max_release_batch, events)
        self.last_origins = origins
        return lines

    def released_origins(self) -> Optional[List[int]]:
        return self.last_origins

    def stats(self) -> Dict:
        return {
            "claims_seen": self.claims_seen,
            "releases": self.releases,
            "max_release_batch": self.max_release_batch,
            "peak_buffer_events": self.peak_buffer_events,
            "peak_open_timepoints": self.peak_open_timepoints,
            "released_unclaimed_at_eof": self.released_unclaimed,
            "final_frontier": self.frontier,
            "stream_format": self.stream_format or "csv",
        }
