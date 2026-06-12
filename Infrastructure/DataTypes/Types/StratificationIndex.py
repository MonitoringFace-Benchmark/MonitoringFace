from bisect import bisect_right


class StratificationIndex:
    """Maps between an original (multi-event) trace and its stratified
    (one-event-per-tp) form, given per-timepoint event counts."""

    def __init__(self, events_per_tp: dict[int, int]):
        self.tps = sorted(events_per_tp)                  # original tps, in order
        self.boundaries = [0]                             # prefix sums; len = T+1
        for tp in self.tps:
            self.boundaries.append(self.boundaries[-1] + events_per_tp[tp])
        self._pos = {tp: i for i, tp in enumerate(self.tps)}  # original tp -> index

    @property
    def total(self) -> int:
        return self.boundaries[-1]                        # number of stratified tps

    # stratified -> original
    def original(self, x: int) -> tuple[int, int]:
        if self.total == 0:
            raise IndexError("empty index: no timepoints")
        x = min(max(x, 0), self.total - 1)  # clamp into [0, total-1]
        i = bisect_right(self.boundaries, x) - 1
        return self.tps[i], x - self.boundaries[i]  # (original_tp, event_pos)

    # original -> stratified
    def stratified_range(self, original_tp: int) -> tuple[int, int]:
        i = self._pos[original_tp]
        return self.boundaries[i], self.boundaries[i + 1] # half-open [start, end)

    def boundary(self, original_tp: int) -> int:
        """Last stratified tp of the block — where the aggregated verdict completes."""
        return self.boundaries[self._pos[original_tp] + 1] - 1

    def is_boundary(self, x: int) -> bool:
        """True iff x is the final stratified tp of its block (verdict-valid point)."""
        i = bisect_right(self.boundaries, x) - 1
        return x == self.boundaries[i + 1] - 1