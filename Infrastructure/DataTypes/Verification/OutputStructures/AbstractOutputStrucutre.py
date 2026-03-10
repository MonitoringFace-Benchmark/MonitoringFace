from abc import ABC, abstractmethod
from typing import List


class AbstractOutputStructure(ABC):
    @abstractmethod
    def retrieve_order(self) -> List[str]:
        pass
