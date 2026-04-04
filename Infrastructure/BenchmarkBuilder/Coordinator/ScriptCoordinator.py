import shutil
from typing import List, Tuple, Optional, Dict
import hashlib
import os

from Infrastructure.AutoConversion.InputOutputPolicyFormats import InputOutputPolicyFormats
from Infrastructure.AutoConversion.InputOutputTraceFormats import InputOutputTraceFormats
from Infrastructure.BenchmarkBuilder.Coordinator.Coordinator import Coordinator
from Infrastructure.DataTypes.Contracts.OnlineExperimentContract import OnlineExperimentContractGeneral
from Infrastructure.DataTypes.Contracts.SubContracts.ScriptSetupContract import ScriptSetupContract
from Infrastructure.DataTypes.PathManager.PathManager import PathManager
from Infrastructure.DataTypes.Types.custome_type import OnlineOffline
from Infrastructure.constants import PATH_TO_ARCHIVE, FINGERPRINT_DATA, PATH_TO_FOLDER, Signature_File


class ScriptCoordinator(Coordinator):
    def __init__(self, path_manager: PathManager, script_contract: ScriptSetupContract, online_experiment_settings: OnlineExperimentContractGeneral):
        super().__init__(path_manager=path_manager, runtime_settings=OnlineOffline.Online, online_settings=online_experiment_settings, oracle=None)
        self.experiment = online_experiment_settings
        self.contract = script_contract
        self.script_name = self.contract.script_name

        # Archive/CaseStudies/ExperimentName
        self.path_to_script_folder = f"{self.path_manager.get_path(PATH_TO_ARCHIVE)}/CaseStudies/{self.contract.name}"
        self.script_org_path = f"{self.path_to_script_folder}/{self.script_name}"
        self.signature_org_path = f"{self.path_to_script_folder}/{Signature_File()}"

        # Infrastructure/experiments/ExperimentName
        self.path_to_data_folder = f"{self.path_manager.get_path(PATH_TO_FOLDER)}"
        self.script_dst_path = f"{self.path_to_data_folder}/{self.script_name}"
        self.signature_dst_path = f"{self.path_to_data_folder}/{Signature_File()}"

        self.signature = Signature_File() if os.path.exists(self.signature_org_path) else None

    def build(self):
        os.makedirs(self.path_to_data_folder, exist_ok=True)

        shutil.copy(self.script_org_path, self.script_dst_path)

        if os.path.exists(self.signature_org_path):
            shutil.copy(self.signature_org_path, self.signature_dst_path)

    def finger_print(self) -> Dict[str, str]:
        fingerprint_input_file = os.path.join(self.path_to_script_folder, self.script_name)

        if not os.path.exists(fingerprint_input_file):
            raise FileNotFoundError(f"Fingerprint input file not found: {fingerprint_input_file}")

        with open(fingerprint_input_file, "rb") as f:
            first_hash = hashlib.sha256(f.read()).hexdigest()

        second_hash = hashlib.sha256(first_hash.encode("utf-8")).hexdigest()
        return {FINGERPRINT_DATA: second_hash}

    def short_cutting(self):
        pass

    def time_out(self) -> Optional[int]:
        return self.online_settings.accumulated_latency

    def iterate_settings(self) -> List[Tuple[int, str, str, InputOutputTraceFormats, str, InputOutputPolicyFormats, Optional[str], Optional[str]]]:
        return [(0, self.path_to_data_folder, self.script_name, None, None, self.signature, None)]
