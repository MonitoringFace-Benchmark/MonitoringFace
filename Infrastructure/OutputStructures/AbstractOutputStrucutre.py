from abc import ABC, abstractmethod
from typing import Union

from Infrastructure.OutputStructures.Assignment import Assignment


class AbstractOutputStructure(ABC):
    @abstractmethod
    def retrieve_index(self, time_point):
        pass

    @abstractmethod
    def insert_index(self, value, time_point, time_stamp=None):
        pass