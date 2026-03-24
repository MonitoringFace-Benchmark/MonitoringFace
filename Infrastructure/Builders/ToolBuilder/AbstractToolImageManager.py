from abc import ABC, abstractmethod

from Infrastructure.Frontend.CLI.cli_args import CLIArgs


class AbstractToolImageManager(ABC):
    @abstractmethod
    def run_offline(self, path_to_data, parameters, time_on=None, time_out=None, measure=True, name=None):
        pass

    @abstractmethod
    def _build_image(self):
        pass

    @abstractmethod
    def get_image_name(self) -> str:
        pass

    @abstractmethod
    def get_cli_args(self) -> CLIArgs:
        pass
