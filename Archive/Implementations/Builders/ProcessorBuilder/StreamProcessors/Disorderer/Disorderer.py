import random
from typing import Dict, List, Optional

from Infrastructure.Builders.ProcessorBuilder.StreamProcessors.ClaimFamily import (
    SYNTHESIZED_ORIGIN, claim_tp, csv_to_bridge, extract_tp, extract_ts, render_claim, watermark_tp)
from Infrastructure.Builders.ProcessorBuilder.StreamProcessors.StreamProcessorTemplate import (
    StreamProcessorException, StreamProcessorTemplate)

DISTRIBUTIONS = ("uniform", "geometric", "heavytail")
CLAIM_ORDERS = ("independent", "downward-closed")
GRANULARITIES = ("event", "block")
FORMATS = ("csv", "bridge")


class Disorderer(StreamProcessorTemplate):
    buffering = True
    deterministic = True

    def setup(self, params: Dict) -> None:
        if "seed" not in params:
            raise StreamProcessorException("Disorderer requires an explicit 'seed' param")
        self.seed = int(params["seed"])
        self.displacement_bound = int(params.get("displacement_bound", 10))
        if self.displacement_bound < 0:
            raise StreamProcessorException("Disorderer 'displacement_bound' must be >= 0")
        self.delay_distribution = params.get("delay_distribution", "uniform")
        if self.delay_distribution not in DISTRIBUTIONS:
            raise StreamProcessorException(
                f"Disorderer 'delay_distribution' must be one of {DISTRIBUTIONS}")
        self.fraction_displaced = float(params.get("fraction_displaced", 1.0))
        if not 0.0 <= self.fraction_displaced <= 1.0:
            raise StreamProcessorException("Disorderer 'fraction_displaced' must be in [0, 1]")
        self.granularity = params.get("granularity", "event")
        if self.granularity not in GRANULARITIES:
            raise StreamProcessorException(f"Disorderer 'granularity' must be one of {GRANULARITIES}")
        self.lag = int(params.get("lag", 0))
        if self.lag < 0:
            raise StreamProcessorException("Disorderer 'lag' must be >= 0")
        self.claim_order = params.get("claim_order", "independent")
        if self.claim_order not in CLAIM_ORDERS:
            raise StreamProcessorException(f"Disorderer 'claim_order' must be one of {CLAIM_ORDERS}")
        self.format = params.get("format", "csv")
        if self.format not in FORMATS:
            raise StreamProcessorException(f"Disorderer 'format' must be one of {FORMATS}")
        self.base_tp = int(params.get("base_tp", 0))

        self.events: List[tuple] = []
        self.tp_ts: Dict[int, int] = {}
        self.index = 0
        self.last_origins: Optional[List[int]] = None
        self._stats: Dict = {}

    def feed(self, line: str) -> List[str]:
        self.index += 1
        if claim_tp(line) is not None or watermark_tp(line) is not None:
            raise StreamProcessorException(
                f"Disorderer expects a claim-free canonical trace, got {line!r}")
        tp = extract_tp(line)
        ts = extract_ts(line)
        if tp in self.tp_ts and self.tp_ts[tp] != ts:
            raise StreamProcessorException(
                f"Disorderer: inconsistent timestamps for tp {tp}: {self.tp_ts[tp]} vs {ts}")
        self.tp_ts[tp] = ts
        self.events.append((self.index, tp, line))
        self.last_origins = None
        return []

    def flush(self) -> List[str]:
        if not self.events:
            self.last_origins = None
            return []
        return self._materialize()

    def _delay(self, rng) -> int:
        bound = self.displacement_bound
        if bound == 0 or rng.random() >= self.fraction_displaced:
            return 0
        if self.delay_distribution == "uniform":
            return rng.randint(1, bound)
        if self.delay_distribution == "geometric":
            delay = 1
            while delay < bound and rng.random() < 0.5:
                delay += 1
            return delay
        return min(bound, max(1, int(rng.paretovariate(1.5))))

    def _permute(self, rng) -> List[tuple]:
        if self.granularity == "event":
            keyed = [(i + self._delay(rng), i, entry) for i, entry in enumerate(self.events)]
            keyed.sort(key=lambda item: (item[0], item[1]))
            return [entry for _, _, entry in keyed]
        blocks: List[List[tuple]] = []
        for entry in self.events:
            if blocks and blocks[-1][0][1] == entry[1]:
                blocks[-1].append(entry)
            else:
                blocks.append([entry])
        keyed = [(i + self._delay(rng), i, block) for i, block in enumerate(blocks)]
        keyed.sort(key=lambda item: (item[0], item[1]))
        return [entry for _, _, block in keyed for entry in block]

    def _materialize(self) -> List[str]:
        rng_events = random.Random(f"{self.seed}/events")
        rng_claims = random.Random(f"{self.seed}/claims")

        min_tp = min(tp for _, tp, _ in self.events)
        max_tp = max(tp for _, tp, _ in self.events)
        if min_tp != self.base_tp:
            raise StreamProcessorException(
                f"Disorderer: trace starts at tp {min_tp} but base_tp is {self.base_tp}")

        permuted = self._permute(rng_events)
        n = len(permuted)

        # a valid stream carries every time-point's timestamp; never invent one
        missing = [tp for tp in range(self.base_tp, max_tp + 1) if tp not in self.tp_ts]
        if missing:
            raise StreamProcessorException(
                f"Disorderer: invalid canonical stream, time-points {missing} "
                f"carry no timestamp")

        last_position: Dict[int, int] = {}
        for position, (_, tp, _) in enumerate(permuted):
            last_position[tp] = position

        gaps: Dict[int, int] = {}
        for tp in range(self.base_tp, max_tp + 1):
            floor = last_position.get(tp, -1) + 1
            gaps[tp] = min(n, floor + rng_claims.randint(0, self.lag))
        if self.claim_order == "downward-closed":
            running = 0
            for tp in range(self.base_tp, max_tp + 1):
                running = max(running, gaps[tp])
                gaps[tp] = running

        claims_at: Dict[int, List[int]] = {}
        for tp in sorted(gaps):
            claims_at.setdefault(gaps[tp], []).append(tp)

        out: List[str] = []
        origins: List[int] = []
        open_tps = set()
        claimed = set()
        peak_open = 0
        max_displacement = 0
        displacement_sum = 0
        for position in range(n + 1):
            if position > 0:
                original_index, tp, line = permuted[position - 1]
                if tp in claimed:
                    raise StreamProcessorException(
                        f"Disorderer invariant violated: event of tp {tp} after its claim")
                out.append(csv_to_bridge(line) if self.format == "bridge" else line)
                origins.append(original_index)
                open_tps.add(tp)
                displacement = abs((position - 1) - (original_index - 1))
                max_displacement = max(max_displacement, displacement)
                displacement_sum += displacement
                peak_open = max(peak_open, len(open_tps))
            for tp in claims_at.get(position, []):
                out.append(render_claim(tp, self.tp_ts[tp]))
                origins.append(SYNTHESIZED_ORIGIN)
                claimed.add(tp)
                open_tps.discard(tp)

        self._stats = {
            "events": n,
            "timepoints": max_tp - self.base_tp + 1,
            "claims": len(gaps),
            "max_displacement": max_displacement,
            "mean_displacement": round(displacement_sum / n, 3),
            "peak_open_timepoints": peak_open,
            "displacement_bound": self.displacement_bound,
            "lag": self.lag,
            "claim_order": self.claim_order,
            "format": self.format,
        }
        self.events = []
        self.tp_ts = {}
        self.last_origins = origins
        return out

    def released_origins(self) -> Optional[List[int]]:
        return self.last_origins

    def stats(self) -> Dict:
        return dict(self._stats)
