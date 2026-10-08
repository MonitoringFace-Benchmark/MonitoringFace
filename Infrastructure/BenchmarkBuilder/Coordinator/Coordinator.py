from abc import abstractmethod, ABC
from enum import Enum
from typing import List, Tuple, Optional, Dict

from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats
from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats
from Infrastructure.DataTypes.Contracts.OnlineExperimentContract import OnlineExperimentContractGeneral
from Infrastructure.DataTypes.PathManager.PathManager import PathManager
from Infrastructure.DataTypes.Types.custome_type import OnlineOffline
from Infrastructure.Monitors.MonitorExceptions import TimedOut, ToolException
from Infrastructure.Oracles.AbstractOracleTemplate import AbstractOracleTemplate


class SeedType(Enum):
    RANDOM = 1
    FIXED = 2
    DETERMINISTIC = 3


class Coordinator(ABC):
    def __init__(
            self, path_manager: PathManager, runtime_settings: OnlineOffline,
            online_settings: OnlineExperimentContractGeneral,
            oracle: Optional[AbstractOracleTemplate] = None):
        self.path_manager = path_manager
        self.oracle = oracle
        self.online_settings = online_settings
        self.runtime_settings = runtime_settings

    @abstractmethod
    def build(self):
        pass

    @abstractmethod
    def finger_print(self) -> Dict[str, str]:
        pass

    @abstractmethod
    def short_cutting(self):
        pass

    @abstractmethod
    def time_out(self) -> Optional[int]:
        pass

    @abstractmethod
    def iterate_settings(self) -> List[Tuple[int, str, str, InputOutputTraceFormats, str, InputOutputPolicyFormats, Optional[str], Optional[str]]]:
        pass

    def policy_companions(self, identifier: int) -> Dict[str, str]:
        """The files that come with the policy of setting `identifier`, by kind
        (POLICY_COMPANION_KEYS), relative to the setting folder."""
        return {}

    def add_path(self, path_id: str, path: str):
        self.path_manager.add_path(path_id, path)

    def get_path(self, path_id: str) -> Optional[str]:
        return self.path_manager.get_path(path_id)

    def get_path_manager(self) -> PathManager:
        return self.path_manager

    def get_oracle(self) -> Optional[AbstractOracleTemplate]:
        return self.oracle

    def get_runtime_settings(self) -> OnlineOffline:
        return self.runtime_settings

    def get_online_settings(self) -> OnlineExperimentContractGeneral:
        return self.online_settings


def run_guard_monitor(guard, path_to_folder, time_on=None, time_out=None):
    """Run a generation guard's monitor on the inputs its preprocessing prepared.
    path_to_folder is the folder that preprocessing was given: the monitor's
    paths are relative to it, and it is mounted as /data. A run outside
    [time_on, time_out] raises TimedOut from inside run_offline, as does exit
    code 124; any other failure raises ToolException."""
    cmd, name = guard.construct_offline_command()
    out, code = guard.image.run_offline(
        parameters=cmd, path_to_data=path_to_folder, time_on=time_on, time_out=time_out, name=name
    )
    if code == 124:
        raise TimedOut(f"Guard monitor {guard.name} timed out")
    if code == 137:
        raise ToolException("OOM Killer activated")
    if code != 0:
        raise ToolException(f"Guard monitor {guard.name} failed (exit_code={code}): {out}")
