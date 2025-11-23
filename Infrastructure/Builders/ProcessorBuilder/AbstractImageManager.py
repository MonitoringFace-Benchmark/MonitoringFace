from abc import ABC, abstractmethod


class AbstractImageManager(ABC):
    @abstractmethod
    def _build_image(self):
        pass

    @abstractmethod
    def run(self, generic_contract, time_on=None, time_out=None):
        pass
