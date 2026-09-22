from Infrastructure.DataTypes.Verification.OutputStructures.Strength import Comparison
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple


class AbstractOutputStructure(ABC):
    @abstractmethod
    def as_oracle(self, other: 'AbstractOutputStructure') -> Comparison:
        pass

    @abstractmethod
    def retrieve_order(self) -> List[str]:
        pass

    @abstractmethod
    def time_points(self) -> Dict[int, int]:
        pass

    def has_verdicts(self, time_point: int) -> bool:
        return time_point in self.time_points()

    def output_counts(self) -> Tuple[Optional[int], Optional[int]]:
        """(total emitted verdicts, distinct (tp, value) verdicts); the gap
        between the two exposes duplicate emissions. (None, None) for
        structures without per-tp verdict storage."""
        by_tp = getattr(self, "by_tp", None)
        if by_tp is None:
            return None, None
        total = 0
        distinct = set()
        for tp, entries in by_tp.items():
            for _, _, values in entries:
                total += len(values)
                for value in values:
                    distinct.add((tp, str(value)))
        return total, len(distinct)
