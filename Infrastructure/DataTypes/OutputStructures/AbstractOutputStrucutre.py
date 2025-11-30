from abc import ABC, abstractmethod


class AbstractOutputStructure(ABC):
    @abstractmethod
    def retrieve_index(self, time_point):
        pass

    @abstractmethod
    def insert_index(self, value, time_point, time_stamp=None):
        pass