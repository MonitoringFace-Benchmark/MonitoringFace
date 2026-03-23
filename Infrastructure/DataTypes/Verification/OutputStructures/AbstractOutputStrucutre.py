from abc import ABC, abstractmethod
from typing import List, Dict, Tuple


class AbstractOutputStructure(ABC):
    @abstractmethod
    def as_oracle(self, other: 'AbstractOutputStructure') -> Tuple[bool, str]:
        pass

    @abstractmethod
    def retrieve_order(self) -> List[str]:
        pass

    @abstractmethod
    def time_points(self) -> Dict[int, int]:
        pass
