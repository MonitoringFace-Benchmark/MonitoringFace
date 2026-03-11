from abc import ABC, abstractmethod
from typing import List, Dict


class AbstractOutputStructure(ABC):
    @abstractmethod
    def retrieve_order(self) -> List[str]:
        pass

    @abstractmethod
    def time_points(self) -> Dict[int, int]:
        pass
