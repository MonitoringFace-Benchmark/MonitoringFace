import os
from typing import Dict, Any, List, Optional, Union
from omegaconf import OmegaConf, DictConfig
from hydra import compose, initialize_config_dir
from hydra.core.global_hydra import GlobalHydra

from Infrastructure.Builders.ProcessorBuilder.DataGenerators.DataGolfGenerator.DataGolfContract import DataGolfContract
from Infrastructure.Builders.ProcessorBuilder.DataGenerators.PatternGenerator.PatternGeneratorContract import Patterns
from Infrastructure.Builders.ProcessorBuilder.DataGenerators.SignatureGenerator.SignatureGeneratorContract import Signature
from Infrastructure.Builders.ProcessorBuilder.PolicyGenerators.MfotlPolicyGenerator.MfotlPolicyContract import MfotlPolicyContract
from Infrastructure.Builders.ToolBuilder.ToolManager import ToolManager
from Infrastructure.DataTypes.Contracts.BenchmarkContract import (
    DataGenerators, SyntheticBenchmarkContract, PolicyGenerators, CaseStudyBenchmarkContract
)
from Infrastructure.DataTypes.Contracts.SubContracts.SyntheticContract import SyntheticExperiment
from Infrastructure.DataTypes.Contracts.SubContracts.TimeBounds import TimeGuarded, TimeGuardingTool
from Infrastructure.DataTypes.Types.custome_type import ExperimentType, BranchOrRelease
from Infrastructure.Monitors.MonitorManager import MonitorManager
from Infrastructure.Oracles.OracleManager import OracleManager


class YamlParserException(Exception):
    pass


class YamlParser:
    """Parse YAML configuration files using Hydra for benchmark experiments"""
    
    def __init__(self, yaml_path: str, path_to_build: str = None, path_to_experiments: str = None):
        """
        Initialize the YAML parser with Hydra
        
        Args:
            yaml_path: Path to the YAML configuration file
            path_to_build: Path to the build directory (optional, will use default)
            path_to_experiments: Path to experiments directory (optional, will use default)
        """
        self.yaml_path = os.path.abspath(yaml_path)
        self.config_dir = os.path.dirname(self.yaml_path)
        self.config_name = os.path.splitext(os.path.basename(self.yaml_path))[0]
        
        # Setup paths
        your_path_to_mfb = os.getcwd()
        self.path_to_project = your_path_to_mfb
        self.path_to_build = path_to_build or f"{your_path_to_mfb}/Infrastructure/build"
        self.path_to_experiments = path_to_experiments or f"{your_path_to_mfb}/Infrastructure/experiments"
        
        # Ensure directories exist
        os.makedirs(self.path_to_build, exist_ok=True)
        os.makedirs(self.path_to_experiments, exist_ok=True)
        
        # Load configuration using Hydra
        self.cfg = self._load_config()
    
    def _load_config(self) -> DictConfig:
        """Load YAML configuration using Hydra"""
        # Clear any existing Hydra instance
        GlobalHydra.instance().clear()
        
        try:
            # Initialize Hydra with the config directory
            initialize_config_dir(config_dir=self.config_dir, version_base=None)
            
            # Compose configuration
            cfg = compose(config_name=self.config_name)
            
            return cfg
        except Exception as e:
            raise YamlParserException(f"Error loading configuration: {e}")
        finally:
            # Don't clear here - we need the config later
            pass
    
    @staticmethod
    def _parse_branch_or_release(value: str) -> BranchOrRelease:
        """Convert string to BranchOrRelease enum"""
        value_lower = value.lower()
        if value_lower == "branch":
            return BranchOrRelease.Branch
        elif value_lower == "release":
            return BranchOrRelease.Release
        else:
            raise YamlParserException(f"Invalid branch_or_release value: {value}. Must be 'branch' or 'release'")
    
    @staticmethod
    def _parse_experiment_type(value: str) -> ExperimentType:
        """Convert string to ExperimentType enum"""
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
        """Convert string to TimeGuardingTool enum"""
        value_lower = value.lower()
        if value_lower == "monitor":
            return TimeGuardingTool.Monitor
        elif value_lower == "oracle":
            return TimeGuardingTool.Oracle
        elif value_lower == "generator":
            return TimeGuardingTool.Generator
        else:
            raise YamlParserException(f"Invalid guard_type value: {value}")
    
    @staticmethod
    def _parse_data_generators(value: str) -> DataGenerators:
        """Convert string to DataGenerators enum"""
        value_upper = value.upper()
        if value_upper == "DATAGENERATOR":
            return DataGenerators.DATAGENERATOR
        elif value_upper == "DATAGOLF":
            return DataGenerators.DATAGOLF
        elif value_upper == "PATTERNS":
            return DataGenerators.PATTERNS
        else:
            raise YamlParserException(f"Invalid data_source value: {value}")
    
    @staticmethod
    def _parse_policy_generators(value: str) -> PolicyGenerators:
        """Convert string to PolicyGenerators enum"""
        value_upper = value.upper()
        if value_upper == "MFOTLGENERATOR":
            return PolicyGenerators.MFOTLGENERATOR
        elif value_upper == "PATTERNS":
            return PolicyGenerators.PATTERNS
        else:
            raise YamlParserException(f"Invalid policy_source value: {value}")
    
    def parse_tool_manager(self) -> ToolManager:
        """Parse tools configuration and create ToolManager"""
        if 'tools' not in self.cfg:
            raise YamlParserException("Missing 'tools' section in YAML configuration")
        
        tools_to_build = []
        for tool in self.cfg.tools:
            name = tool.get('name')
            branch = tool.get('branch')
            release = tool.get('release', 'branch')
            
            if not name or not branch:
                raise YamlParserException(f"Tool configuration missing 'name' or 'branch': {tool}")
            
            tools_to_build.append((name, branch, self._parse_branch_or_release(release)))
        
        return ToolManager(tools_to_build=tools_to_build, path_to_project=self.path_to_project)
    
    def parse_data_setup(self) -> Union[Signature, Patterns, DataGolfContract]:
        """Parse data setup configuration"""
        if 'data_setup' not in self.cfg:
            raise YamlParserException("Missing 'data_setup' section in YAML configuration")
        
        data_setup = self.cfg.data_setup
        data_type = data_setup.get('type')
        
        if data_type == 'Signature':
            config = OmegaConf.to_container(data_setup.get('Signature', {}), resolve=True)
            return Signature(**config)
        elif data_type == 'Patterns':
            config = OmegaConf.to_container(data_setup.get('Patterns', {}), resolve=True)
            return Patterns(**config)
        elif data_type == 'DataGolfContract':
            config = OmegaConf.to_container(data_setup.get('DataGolfContract', {}), resolve=True)
            # Add path if not specified
            if 'path' not in config:
                config['path'] = self.path_to_experiments
            return DataGolfContract(**config)
        else:
            raise YamlParserException(f"Invalid data_setup type: {data_type}")
    
    def parse_policy_setup(self) -> MfotlPolicyContract:
        """Parse policy setup configuration"""
        if 'policy_setup' not in self.cfg:
            raise YamlParserException("Missing 'policy_setup' section in YAML configuration")
        
        policy_setup = self.cfg.policy_setup
        policy_type = policy_setup.get('type', 'PolicyGeneratorContract')
        
        if policy_type == 'PolicyGeneratorContract':
            # Start with default contract
            contract = MfotlPolicyContract().default_contract()
            # Update with provided config
            config = OmegaConf.to_container(policy_setup, resolve=True)
            for key, value in config.items():
                if key != 'type' and hasattr(contract, key) and value is not None:
                    setattr(contract, key, value)
            return contract
        else:
            raise YamlParserException(f"Invalid policy_setup type: {policy_type}")
    
    def parse_benchmark_contract(self) -> Union[SyntheticBenchmarkContract, CaseStudyBenchmarkContract]:
        """Parse benchmark contract based on benchmark type"""
        experiment_name = self.cfg.get('experiment_name', 'unnamed_experiment')
        benchmark_type = self.cfg.get('benchmark_type', 'synthetic')
        
        if benchmark_type == 'case_study':
            case_study_config = self.cfg.get('case_study_config', {})
            case_study_name = case_study_config.get('case_study_name')
            
            if not case_study_name:
                raise YamlParserException("Missing 'case_study_name' in case_study_config")
            
            return CaseStudyBenchmarkContract(
                experiment_name=experiment_name,
                case_study_name=case_study_name
            )
        
        elif benchmark_type == 'synthetic':
            if 'synthetic_config' not in self.cfg:
                raise YamlParserException("Missing 'synthetic_config' for synthetic benchmark")
            
            synthetic_config = self.cfg.synthetic_config
            data_source = self._parse_data_generators(synthetic_config.get('data_source', 'DATAGENERATOR'))
            policy_source = self._parse_policy_generators(synthetic_config.get('policy_source', 'MFOTLGENERATOR'))
            
            experiment_config = synthetic_config.get('experiment', {})
            experiment_dict = OmegaConf.to_container(experiment_config, resolve=True)
            experiment = SyntheticExperiment(
                num_operators=experiment_dict.get('num_operators', [5]),
                num_fvs=experiment_dict.get('num_fvs', [2]),
                num_setting=experiment_dict.get('num_setting', [0]),
                num_data_set_sizes=experiment_dict.get('num_data_set_sizes', [50])
            )
            
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
            params = monitor_dict.get('params', {})
            
            if not identifier or not name or not branch:
                raise YamlParserException(f"Monitor configuration missing required fields: {monitor_dict}")
            
            # Add path_to_project to params if not present (used by ImageManager internally)
            if 'path_to_project' not in params:
                params['path_to_project'] = self.path_to_project
            
            monitors_to_build.append((identifier, name, branch, params))
        
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
        """Parse time guard configuration and create TimeGuarded"""
        time_guard_config = self.cfg.get('time_guard', {})
        time_guard_dict = OmegaConf.to_container(time_guard_config, resolve=True)
        
        enabled = time_guard_dict.get('enabled', False)
        lower_bound = time_guard_dict.get('lower_bound')
        upper_bound = time_guard_dict.get('upper_bound', 200)
        guard_type_str = time_guard_dict.get('guard_type', 'Monitor')
        guard_name = time_guard_dict.get('guard_name')
        
        guard_type = self._parse_time_guarding_tool(guard_type_str)
        
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
        oracle_dict = OmegaConf.to_container(oracle_config, resolve=True)
        if oracle_dict.get('enabled', False):
            return oracle_dict.get('name')
        return None
    
    def get_experiment_type(self) -> ExperimentType:
        """Get experiment type"""
        exp_type_str = self.cfg.get('experiment_type', 'Signature')
        return self._parse_experiment_type(exp_type_str)
    
    def parse_experiment(self) -> Dict[str, Any]:
        """
        Parse entire experiment configuration and return all components
        
        Returns:
            Dictionary containing all parsed components needed to run the experiment
        """
        tool_manager = self.parse_tool_manager()
        data_setup = self.parse_data_setup()
        benchmark_contract = self.parse_benchmark_contract()
        monitor_manager = self.parse_monitor_manager(tool_manager)
        oracle_manager = self.parse_oracle_manager(monitor_manager)
        time_guarded = self.parse_time_guarded(monitor_manager)
        tools_to_build = self.get_tools_to_build()
        experiment_type = self.get_experiment_type()
        oracle_name = self.get_oracle_config()
        
        oracle_tuple = (oracle_manager, oracle_name) if oracle_manager and oracle_name else None
        
        return {
            'tool_manager': tool_manager,
            'data_setup': data_setup,
            'benchmark_contract': benchmark_contract,
            'monitor_manager': monitor_manager,
            'oracle_manager': oracle_manager,
            'time_guarded': time_guarded,
            'tools_to_build': tools_to_build,
            'experiment_type': experiment_type,
            'oracle': oracle_tuple,
            'path_to_project': self.path_to_project,
            'path_to_build': self.path_to_build,
            'path_to_experiments': self.path_to_experiments
        }
    
    def __del__(self):
        """Cleanup Hydra instance"""
        try:
            GlobalHydra.instance().clear()
        except:
            pass


class ExperimentSuiteParser:
    """Parse YAML files containing multiple experiment configurations using Hydra"""
    
    def __init__(self, path_to_project: str, config_name: str):
        """
        Initialize the experiment suite parser
        
        Args:
            suite_yaml_path: Path to the YAML file containing experiment suite
        """
        self.config_dir = f"{path_to_project}/Archive/Benchmarks"
        self.config_name = config_name
        self.cfg = self._load_config()
    
    def _load_config(self) -> DictConfig:
        """Load YAML configuration using Hydra"""
        GlobalHydra.instance().clear()
        
        try:
            initialize_config_dir(config_dir=self.config_dir, version_base=None)
            cfg = compose(config_name=self.config_name)
            return cfg
        except Exception as e:
            raise YamlParserException(f"Error loading suite configuration: {e}")
    
    def get_experiment_paths(self) -> List[str]:
        """
        Get list of enabled experiment configuration paths
        
        Returns:
            List of absolute paths to experiment YAML files
        """
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
        """
        Parse all enabled experiments in the suite
        
        Returns:
            List of parsed experiment configurations
        """
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
        """Cleanup Hydra instance"""
        try:
            GlobalHydra.instance().clear()
        except:
            pass
