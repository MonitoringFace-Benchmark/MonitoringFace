from abc import ABC, abstractmethod


class AbstractToolImageManager(ABC):
    @abstractmethod
    def run(self, path_to_data, parameters, time_on=None, timeout=None):
        pass

    @abstractmethod
    def _build_image(self):
        pass
