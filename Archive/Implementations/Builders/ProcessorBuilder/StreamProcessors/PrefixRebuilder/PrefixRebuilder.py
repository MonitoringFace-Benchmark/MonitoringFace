from typing import Dict, List, Optional

from Infrastructure.Builders.ProcessorBuilder.StreamProcessors.ClaimFamily import (
    SYNTHESIZED_ORIGIN, claim_tp, extract_tp, render_watermark, watermark_tp)
from Infrastructure.Builders.ProcessorBuilder.StreamProcessors.StreamProcessorTemplate import (
    StreamProcessorTemplate)


class PrefixRebuilder(StreamProcessorTemplate):
    """Claim adapter for watermark monitors that handle out-of-order data but
    only understand downward-closed claims: events pass through immediately
    and unsorted, point claims are absorbed into a set, and whenever the
    frontier advances a single watermark for the new maximal complete prefix
    is emitted. Only claims are ever withheld, never events.

    Watermarks are exclusive on both sides, matching the consumers:
    `>WATERMARK n<` settles exactly the time points strictly below n
    (TimelyMon finalizes tp < n on capability downgrade, OOOMon turns it
    into the half-open range claim [previous, n)). A claimed prefix 0..k
    is therefore announced as WATERMARK k+1, and an incoming WATERMARK w
    asserts only 0..w-1."""

    buffering = True
    deterministic = True

    def setup(self, params: Dict) -> None:
        self.frontier = int(params.get("base_tp", 0))
        self.claims = set()
        self.index = 0
        self.dropped = 0
        self.last_origins: Optional[List[int]] = None
        self.max_tp_seen: Optional[int] = None
        self.claims_seen = 0
        self.watermarks_emitted = 0
        self.pending_peak = 0

    def feed(self, line: str) -> List[str]:
        self.index += 1
        claim = claim_tp(line)
        watermark = watermark_tp(line)
        if claim is not None:
            self.claims_seen += 1
            self.claims.add(claim)
            return self._advance()
        if watermark is not None:
            self.claims_seen += 1
            self.claims.update(range(self.frontier, watermark))
            return self._advance()
        tp = extract_tp(line)
        self.max_tp_seen = tp if self.max_tp_seen is None else max(self.max_tp_seen, tp)
        self.last_origins = [self.index]
        return [line]

    def _advance(self) -> List[str]:
        moved = False
        while self.frontier in self.claims:
            self.claims.discard(self.frontier)
            self.frontier += 1
            moved = True
        self.pending_peak = max(self.pending_peak, len(self.claims))
        if not moved:
            self.dropped += 1
            self.last_origins = None
            return []
        self.watermarks_emitted += 1
        self.last_origins = [SYNTHESIZED_ORIGIN]
        return [render_watermark(self.frontier)]

    def flush(self) -> List[str]:
        if self.max_tp_seen is None or self.frontier > self.max_tp_seen:
            self.last_origins = None
            return []
        self.watermarks_emitted += 1
        self.last_origins = [SYNTHESIZED_ORIGIN]
        return [render_watermark(self.max_tp_seen + 1)]

    def released_origins(self) -> Optional[List[int]]:
        return self.last_origins

    def stats(self) -> Dict:
        return {
            "claims_seen": self.claims_seen,
            "watermarks_emitted": self.watermarks_emitted,
            "pending_claims_peak": self.pending_peak,
            "final_frontier": self.frontier,
        }
