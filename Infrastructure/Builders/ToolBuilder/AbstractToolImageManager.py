from abc import ABC, abstractmethod

from Infrastructure.Builders.BuilderUtilities import ContainerRun
from Infrastructure.Frontend.CLI.cli_args import CLIArgs


class AbstractToolImageManager(ABC):
    @abstractmethod
    def run_offline_streams(self, path_to_data, parameters, time_on=None, time_out=None, measure=True,
                            name=None) -> ContainerRun:
        pass

    def run_offline(self, path_to_data, parameters, time_on=None, time_out=None, measure=True, name=None):
        """(output, code), both streams together; run_offline_streams keeps
        them apart for the callers that parse verdicts."""
        run = self.run_offline_streams(path_to_data, parameters, time_on=time_on, time_out=time_out,
                                       measure=measure, name=name)
        return run.output, run.code

    @abstractmethod
    def _build_image(self):
        pass

    @abstractmethod
    def get_image_name(self) -> str:
        pass

    @abstractmethod
    def get_cli_args(self) -> CLIArgs:
        pass
