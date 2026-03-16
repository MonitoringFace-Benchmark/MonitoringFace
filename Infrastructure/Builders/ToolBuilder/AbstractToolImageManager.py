from abc import ABC, abstractmethod


class AbstractToolImageManager(ABC):
    @abstractmethod
    def run_offline(self, path_to_data, parameters, time_on=None, time_out=None, measure=True, name=None):
        pass

    @abstractmethod
    def run_online(self, path_to_data, data_file, parameters, maximum_latency=None, accumulative_time=None, name=None, latency_marker=None):
        pass

    @abstractmethod
    def _build_image(self):
        pass
