import importlib
import os
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple
from omegaconf import OmegaConf, DictConfig
from hydra import compose, initialize_config_dir
from hydra.core.global_hydra import GlobalHydra

from Infrastructure.Builders.ProcessorBuilder.DataGenerators.DataGeneratorTemplate import DataGeneratorTemplate
from Infrastructure.Builders.ProcessorBuilder.PolicyGenerators.PolicyGeneratorTemplate import PolicyGeneratorTemplate

from Infrastructure.Builders.ToolBuilder.ToolManager import ToolManager
from Infrastructure.CLI.cli_args import CLIArgs
from Infrastructure.DataTypes.Contracts.AbstractContract import AbstractContract
from Infrastructure.DataTypes.Contracts.BenchmarkContract import SyntheticBenchmarkContract, CaseStudyBenchmarkContract
from Infrastructure.DataTypes.Contracts.SubContracts.SyntheticContract import SyntheticExperiment
from Infrastructure.DataTypes.Contracts.SubContracts.TimeBounds import TimeGuarded, TimeGuardingTool
from Infrastructure.DataTypes.Types.custome_type import ExperimentType, BranchOrRelease
from Infrastructure.Monitors.MonitorManager import MonitorManager
from Infrastructure.Oracles.OracleManager import OracleManager


class YamlParserException(Exception):
    pass


class YamlParser:
    def __init__(self, yaml_path: str, path_to_build: str = None, path_to_experiments: str = None):
        self.yaml_path = os.path.abspath(yaml_path)
        self.config_dir = os.path.dirname(self.yaml_path)
        self.config_name = os.path.splitext(os.path.basename(self.yaml_path))[0]

        your_path_to_mfb = os.getcwd()
        self.path_to_project = your_path_to_mfb
        self.path_to_build = path_to_build or f"{your_path_to_mfb}/Infrastructure/build"
        self.path_to_experiments = path_to_experiments or f"{your_path_to_mfb}/Infrastructure/experiments"

        os.makedirs(self.path_to_build, exist_ok=True)
        os.makedirs(self.path_to_experiments, exist_ok=True)

        self.cfg = self._load_config()
    
    def _load_config(self) -> DictConfig:
        GlobalHydra.instance().clear()
        try:
            initialize_config_dir(config_dir=self.config_dir, version_base=None)
            cfg = compose(config_name=self.config_name)
            return cfg
        except Exception as e:
            raise YamlParserException(f"Error loading configuration: {e}")
        finally:
            pass
    
    @staticmethod
    def _parse_branch_or_release(value: str) -> BranchOrRelease:
        value_lower = value.lower()
        if value_lower == "branch":
            return BranchOrRelease.Branch
        elif value_lower == "release":
            return BranchOrRelease.Release
        else:
            raise YamlParserException(f"Invalid branch_or_release value: {value}. Must be 'branch' or 'release'")
    
    @staticmethod
    def _parse_experiment_type(value: str) -> ExperimentType:
        value_lower = value.lower()
        if value_lower == "pattern":
            return ExperimentType.Pattern
        elif value_lower == "signature":
            return ExperimentType.Signature
        elif value_lower == "casestudy":
            return ExperimentType.CaseStudy
        else:
            raise YamlParserException(f"Invalid experiment_type value: {value}")
    
    @staticmethod
    def _parse_time_guarding_tool(value: str) -> TimeGuardingTool:
        value_lower = value.lower()
        if value_lower == "monitor":
            return TimeGuardingTool.Monitor
        elif value_lower == "oracle":
            return TimeGuardingTool.Oracle
        elif value_lower == "generator":
            return TimeGuardingTool.Generator
        else:
            raise YamlParserException(f"Invalid guard_type value: {value}")
    
    def parse_tool_manager(self, cli_args: CLIArgs) -> ToolManager:
        if 'tools' not in self.cfg:
            raise YamlParserException("Missing 'tools' section in YAML configuration")
        
        tools_to_build = []
        for tool in self.cfg.tools:
            name = tool.get('name')
            branch = tool.get('branch')
            commit = tool.get('commit')
            release = tool.get('release', 'branch')
            
            if not name or not branch:
                raise YamlParserException(f"Tool configuration missing 'name' or 'branch': {tool}")
            
            tools_to_build.append((name, branch, commit, self._parse_branch_or_release(release)))
        
        return ToolManager(tools_to_build=tools_to_build, path_to_project=self.path_to_project, cli_args=cli_args)

    def parse_seeds(self) -> Optional[Dict[str, Tuple[int, int]]]:
        if 'seeds' not in self.cfg:
            return None
        return OmegaConf.to_container(self.cfg.seeds, resolve=True)

    @staticmethod
    def _parse_data_generators(path_to_module, name: str) -> DataGeneratorTemplate:
        print(f"-> Attempting to initialize Policy Generator {name}")
        available = _discover_names(f"{path_to_module}/Infrastructure", "DataGenerators")
        if name in available:
            cls = _retrieve_module("DataGenerators", name)
            build_cls = cls(name=name, path_to_build=f"{path_to_module}")
            print("    -> (Success)")
            return build_cls
        else:
            raise YamlParserException(f"Invalid DataGenerator {name} not in {available}")

    def parse_data_generator_setup(self) -> AbstractContract:
        if 'data_setup' not in self.cfg:
            raise YamlParserException("Missing 'data_setup' section in YAML configuration")
        
        data_setup = self.cfg.data_setup
        data_contract_name = data_setup.get('type')

        folder_files = _discover_contract_names(self.path_to_project + "/Infrastructure", "DataGenerators")
        if _contract_names(folder_files, data_contract_name):
            folder = _folder_name_from_contract(folder_files, data_contract_name)
            config = OmegaConf.to_container(data_setup.get(data_contract_name, {}), resolve=True)
            contract = _retrieve_contract("DataGenerators", folder, data_contract_name)
            return contract(**config)
        else:
            raise YamlParserException(f"Invalid data_setup type: {data_contract_name}")

    @staticmethod
    def _parse_policy_generators(path_to_module, name: str) -> PolicyGeneratorTemplate:
        print(f"-> Attempting to initialize Policy Generator {name}")
        available = _discover_names(f"{path_to_module}/Infrastructure", "PolicyGenerators")
        if name in available:
            cls = _retrieve_module("PolicyGenerators", name)
            build_cls = cls(name=name, path_to_build=f"{path_to_module}")
            print("    -> (Success)")
            return build_cls
        else:
            raise YamlParserException(f"Invalid Policy Generator {name} not in {available}")
    
    def parse_policy_setup(self):
        if 'policy_setup' not in self.cfg:
            raise YamlParserException("Missing 'policy_setup' section in YAML configuration")
        
        policy_setup = self.cfg.policy_setup
        data_contract_name = policy_setup.get('type')

        folder_files = _discover_contract_names(self.path_to_project + "/Infrastructure", "PolicyGenerators")
        if _contract_names(folder_files, data_contract_name):
            folder = _folder_name_from_contract(folder_files, data_contract_name)
            config = OmegaConf.to_container(policy_setup.get(data_contract_name, {}), resolve=True)
            contract = _retrieve_contract("PolicyGenerators", folder, data_contract_name)
            return contract().instantiate_contract(config)
        else:
            raise YamlParserException(f"Invalid Policy Generator Contract: {data_contract_name}")
    
    def parse_benchmark_contract(self) -> Union[SyntheticBenchmarkContract, CaseStudyBenchmarkContract]:
        experiment_name = self.cfg.get('experiment_name', 'unnamed_experiment')
        benchmark_type = self.cfg.get('benchmark_type', 'synthetic')
        
        if benchmark_type == 'case_study':
            case_study_config = self.cfg.get('case_study_config', {})
            case_study_name = case_study_config.get('case_study_name')
            
            if not case_study_name:
                raise YamlParserException("Missing 'case_study_name' in case_study_config")
            
            return CaseStudyBenchmarkContract(experiment_name=experiment_name, case_study_name=case_study_name)
        elif benchmark_type == 'synthetic':
            if 'synthetic_config' not in self.cfg:
                raise YamlParserException("Missing 'synthetic_config' for synthetic benchmark")
            
            synthetic_config = self.cfg.synthetic_config
            
            experiment_config = synthetic_config.get('experiment', {})
            experiment_dict = OmegaConf.to_container(experiment_config, resolve=True)
            experiment = SyntheticExperiment(
                num_operators=experiment_dict.get('num_operators', [5]),
                num_fvs=experiment_dict.get('num_fvs', [2]),
                num_setting=experiment_dict.get('num_setting', [0]),
                num_data_set_sizes=experiment_dict.get('num_data_set_sizes', [50])
            )

            # todo the discovery of data_source and policy_source could be improved
            data_source = self._parse_data_generators(self.path_to_project, synthetic_config.get('data_source', 'SignatureGenerator'))
            policy_source = self._parse_policy_generators(self.path_to_project, synthetic_config.get('policy_source', 'MfotlPolicyGenerator'))
            policy_setup = self.parse_policy_setup()
            
            return SyntheticBenchmarkContract(
                experiment_name=experiment_name,
                data_source=data_source,
                policy_source=policy_source,
                policy_setup=policy_setup,
                experiment=experiment
            )
        else:
            raise YamlParserException(f"Invalid benchmark_type: {benchmark_type}. Must be 'synthetic' or 'case_study'")
    
    def parse_monitor_manager(self, tool_manager: ToolManager) -> MonitorManager:
        """Parse monitors configuration and create MonitorManager"""
        if 'monitors' not in self.cfg:
            raise YamlParserException("Missing 'monitors' section in YAML configuration")
        
        monitors_to_build = []
        for monitor in self.cfg.monitors:
            monitor_dict = OmegaConf.to_container(monitor, resolve=True)
            identifier = monitor_dict.get('identifier')
            name = monitor_dict.get('name')
            branch = monitor_dict.get('branch')
            commit = monitor_dict.get('commit')
            params = monitor_dict.get('params', {})
            
            if not identifier or not name or not branch:
                raise YamlParserException(f"Monitor configuration missing required fields: {monitor_dict}")
            
            # Add path_to_project to params if not present (used by ImageManager internally)
            if 'path_to_project' not in params:
                params['path_to_project'] = self.path_to_project
            
            monitors_to_build.append((identifier, name, branch, commit, params))
        
        return MonitorManager(tool_manager=tool_manager, monitors_to_build=monitors_to_build)
    
    def parse_oracle_manager(self, monitor_manager: MonitorManager) -> Optional[OracleManager]:
        """Parse oracles configuration and create OracleManager"""
        if 'oracles' not in self.cfg or not self.cfg.oracles:
            return None
        
        oracles_to_build = []
        for oracle in self.cfg.oracles:
            oracle_dict = OmegaConf.to_container(oracle, resolve=True)
            identifier = oracle_dict.get('identifier')
            name = oracle_dict.get('name')
            monitor_name = oracle_dict.get('monitor_name')
            params = oracle_dict.get('params', {})
            
            if not identifier or not name:
                raise YamlParserException(f"Oracle configuration missing required fields: {oracle_dict}")
            
            # OracleManager expects: (oracle_name, identifier, monitor_name, params)
            oracles_to_build.append((name, identifier, monitor_name, params))
        
        return OracleManager(oracles_to_build=oracles_to_build, monitor_manager=monitor_manager)
    
    def parse_time_guarded(self, monitor_manager: MonitorManager) -> TimeGuarded:
        if 'time_guard' not in self.cfg:
            return None
        time_guard_config = self.cfg.get('time_guard', {})
        time_guard_dict = OmegaConf.to_container(time_guard_config, resolve=True)
        
        enabled = time_guard_dict.get('enabled', False)
        lower_bound = time_guard_dict.get('lower_bound')
        upper_bound = time_guard_dict.get('upper_bound')
        guard_type_str = time_guard_dict.get('guard_type')
        guard_name = time_guard_dict.get('guard_name')
        
        guard_type = self._parse_time_guarding_tool(guard_type_str) if guard_type_str else None
        
        return TimeGuarded(
            time_guarded=enabled,
            lower_bound=lower_bound,
            upper_bound=upper_bound,
            guard_type=guard_type,
            guard_name=guard_name,
            monitor_manager=monitor_manager
        )
    
    def get_tools_to_build(self) -> List[str]:
        """Get list of tool names to build"""
        tools = self.cfg.get('tools_to_build', [])
        return OmegaConf.to_container(tools, resolve=True) if tools else []
    
    def get_oracle_config(self) -> Optional[str]:
        """Get oracle configuration name"""
        oracle_config = self.cfg.get('oracle', {})
        if isinstance(oracle_config, dict):
            oracle_dict = oracle_config
        else:
            oracle_dict = OmegaConf.to_container(oracle_config, resolve=True)

        if not oracle_dict:
            return None

        if oracle_dict.get('enabled', False):
            return oracle_dict.get('name')
        return None
    
    def get_experiment_type(self) -> ExperimentType:
        exp_type_str = self.cfg.get('experiment_type', 'Signature')
        return self._parse_experiment_type(exp_type_str)

    def get_repeat_experiments(self) -> int:
        if 'repeats' not in self.cfg:
            return 1
        return self.cfg.get('repeats')
    
    def parse_experiment(self, cli_args: CLIArgs) -> Dict[str, Any]:
        tool_manager = self.parse_tool_manager(cli_args=cli_args)
        benchmark_contract = self.parse_benchmark_contract()
        monitor_manager = self.parse_monitor_manager(tool_manager)
        oracle_manager = self.parse_oracle_manager(monitor_manager)
        time_guarded = self.parse_time_guarded(monitor_manager)
        tools_to_build = self.get_tools_to_build()
        oracle_name = self.get_oracle_config()
        experiment_type = self.get_experiment_type()
        repeats = self.get_repeat_experiments()
        oracle_tuple = (oracle_manager, oracle_name) if oracle_manager and oracle_name else None

        is_case_study = experiment_type == ExperimentType.CaseStudy
        return {
            'tool_manager': tool_manager,
            'benchmark_contract': benchmark_contract,
            'monitor_manager': monitor_manager,
            'oracle_manager': oracle_manager,
            'time_guarded': time_guarded,
            'tools_to_build': tools_to_build,
            'experiment_type': experiment_type,
            'oracle': oracle_tuple,
            'repeat_experiments': repeats,
            'data_setup': None if is_case_study else self.parse_data_generator_setup(),
            'seeds': None if is_case_study else self.parse_seeds()
        }

    def __del__(self):
        """Cleanup Hydra instance"""
        try:
            GlobalHydra.instance().clear()
        except Exception():
            pass


class ExperimentSuiteParser:
    def __init__(self, path_to_project: str, config_name: str):
        relative_dir = os.path.dirname(config_name)
        if relative_dir:
            self.config_dir = f"{path_to_project}/Archive/Benchmarks/{relative_dir}"
        else:
            self.config_dir = f"{path_to_project}/Archive/Benchmarks"
        self.config_name = os.path.basename(config_name)
        self.cfg = self._load_config()
    
    def _load_config(self) -> DictConfig:
        GlobalHydra.instance().clear()
        try:
            initialize_config_dir(config_dir=self.config_dir, version_base=None)
            cfg = compose(config_name=self.config_name)
            return cfg
        except Exception as e:
            raise YamlParserException(f"Error loading suite configuration: {e}")
    
    def get_experiment_paths(self) -> List[str]:
        if 'experiments' not in self.cfg:
            raise YamlParserException("Missing 'experiments' section in suite YAML")
        
        experiment_paths = []
        experiments_list = OmegaConf.to_container(self.cfg.experiments, resolve=True)
        for exp_config in experiments_list:
            if exp_config.get('enabled', True):
                rel_path = exp_config.get('path')
                if not rel_path:
                    raise YamlParserException(f"Missing 'path' in experiment configuration: {exp_config}")
                experiment_paths.append(rel_path)
        return experiment_paths
    
    def parse_all_experiments(self) -> List[Dict[str, Any]]:
        experiment_paths = self.get_experiment_paths()
        parsed_experiments = []
        
        for exp_path in experiment_paths:
            try:
                parsed_exp = YamlParser(exp_path).parse_experiment()
                parsed_experiments.append(parsed_exp)
            except Exception as e:
                print(f"Error parsing experiment {exp_path}: {e}")
                raise
        
        return parsed_experiments
    
    def __del__(self):
        try:
            GlobalHydra.instance().clear()
        except Exception():
            pass


def _discover_names(path_to_infra_, category):
    names = []
    for item in Path(f"{path_to_infra_}/Builders/ProcessorBuilder/{category}").iterdir():
        if not item.is_dir() or item.name.startswith('_') or item.name == '__pycache__':
            continue
        names.append(item.name)
    return names


def _retrieve_module(category, name):
    return getattr(importlib.import_module(f"Infrastructure.Builders.ProcessorBuilder.{category}.{name}.{name}"), name)


def _discover_contract_names(path_to_infra_: str, category: str) -> List[str]:
    contracts = []
    category_path = Path(f"{path_to_infra_}/Builders/ProcessorBuilder/{category}")
    for item in category_path.iterdir():
        if not item.is_dir() or item.name.startswith('_') or item.name == '__pycache__':
            continue
        for file in item.iterdir():
            if file.suffix == '.py' and 'Contract' in file.stem:
                contracts.append((item.name, file.stem))
    return contracts


def _contract_names(folder_file_tuples, name) -> bool:
    return name in map(lambda x: x[1], folder_file_tuples)


def _folder_name_from_contract(folder_file_tuples, contract_name) -> Optional[str]:
    for folder_name, file_name in folder_file_tuples:
        if file_name == contract_name:
            return folder_name
    raise ValueError(f"Contract {contract_name} folder not found")


def _retrieve_contract(category: str, folder_name: str, contract_class_name: str):
    module = importlib.import_module(f"Infrastructure.Builders.ProcessorBuilder.{category}.{folder_name}.{contract_class_name}")
    return getattr(module, contract_class_name)


if __name__ == '__main__':
    path_to_infra = "/Users/krq770/PycharmProjects/MonitoringFace_curr/Infrastructure"
    print(_discover_contract_names(path_to_infra, "DataGenerators"))
    #_discover_processor(path_to_infra, "DataGenerators")
