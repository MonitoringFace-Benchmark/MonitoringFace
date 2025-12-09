"""
Hydra structured configurations for MonitoringFace experiments
Uses dataclasses with OmegaConf for type-safe YAML configuration
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from omegaconf import MISSING


@dataclass
class ToolConfig:
    """Configuration for a monitoring tool"""
    name: str = MISSING
    branch: str = MISSING
    release: str = "branch"  # 'branch' or 'release'


@dataclass
class MonitorConfig:
    """Configuration for a monitor instance"""
    identifier: str = MISSING
    name: str = MISSING
    branch: str = MISSING
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OracleConfig:
    """Configuration for an oracle"""
    identifier: str = MISSING
    name: str = MISSING
    monitor_name: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TimeGuardConfig:
    """Configuration for time guarding"""
    enabled: bool = False
    lower_bound: Optional[int] = None
    upper_bound: int = 200
    guard_type: str = "Monitor"  # 'Monitor', 'Oracle', or 'Generator'
    guard_name: Optional[str] = None


@dataclass
class SignatureDataConfig:
    """Configuration for Signature data generator"""
    trace_length: int = 1000
    seed: Optional[int] = None
    event_rate: int = 1000
    index_rate: Optional[int] = None
    time_stamp: Optional[int] = None
    sig: str = ""
    sample_queue: Optional[int] = None
    string_length: Optional[int] = None
    fresh_value_rate: Optional[float] = None
    domain: Optional[str] = None


@dataclass
class PatternsDataConfig:
    """Configuration for Patterns data generator"""
    trace_length: int = 1000
    seed: Optional[int] = None
    event_rate: int = 1000
    index_rate: Optional[int] = None
    time_stamp: Optional[int] = None
    linear: Optional[int] = None
    interval: Optional[int] = None
    star: Optional[int] = None
    triangle: Optional[int] = None
    pattern: Optional[str] = None
    violations: float = 1.0
    zipf: str = "x=1.5+3,z=2"
    prob_a: float = 0.2
    prob_b: float = 0.3
    prob_c: float = 0.5


@dataclass
class DataGolfDataConfig:
    """Configuration for DataGolf data generator"""
    sig_file: str = MISSING
    formula: str = MISSING
    tup_ts: List[int] = field(default_factory=list)
    tup_amt: int = 100
    tup_val: int = 1
    oracle: bool = True
    no_rewrite: Optional[bool] = None
    trace_length: int = 5
    path: Optional[str] = None


@dataclass
class DataSetupConfig:
    """Configuration for data setup - use one of the specific types"""
    type: str = MISSING  # 'Signature', 'Patterns', or 'DataGolfContract'
    Signature: Optional[SignatureDataConfig] = None
    Patterns: Optional[PatternsDataConfig] = None
    DataGolfContract: Optional[DataGolfDataConfig] = None


@dataclass
class PolicySetupConfig:
    """Configuration for policy setup"""
    type: str = "PolicyGeneratorContract"
    num_preds: int = 4
    prob_eand: Optional[float] = None
    prob_rand: Optional[float] = None
    prob_let: Optional[float] = None
    prob_matchF: Optional[float] = None
    prob_matchP: Optional[float] = None
    # Add other PolicyGeneratorContract fields as needed


@dataclass
class SyntheticExperimentConfig:
    """Configuration for synthetic experiment parameters"""
    num_operators: List[int] = field(default_factory=lambda: [5])
    num_fvs: List[int] = field(default_factory=lambda: [2])
    num_setting: List[int] = field(default_factory=lambda: [0])
    num_data_set_sizes: List[int] = field(default_factory=lambda: [50])


@dataclass
class SyntheticBenchmarkConfig:
    """Configuration for synthetic benchmark"""
    data_source: str = "DATAGENERATOR"  # 'DATAGENERATOR' or 'DATAGOLF'
    policy_source: str = "MFOTLGENERATOR"  # 'MFOTLGENERATOR' or 'PATTERNS'
    experiment: SyntheticExperimentConfig = field(default_factory=SyntheticExperimentConfig)


@dataclass
class CaseStudyBenchmarkConfig:
    """Configuration for case study benchmark"""
    case_study_name: str = MISSING


@dataclass
class OracleExecutionConfig:
    """Configuration for oracle execution"""
    enabled: bool = False
    name: Optional[str] = None


@dataclass
class ExperimentConfig:
    """Main experiment configuration"""
    experiment_name: str = MISSING
    benchmark_type: str = MISSING  # 'synthetic' or 'case_study'
    experiment_type: str = "Signature"  # 'Pattern', 'Signature', or 'CaseStudy'
    
    # Components
    tools: List[ToolConfig] = field(default_factory=list)
    monitors: List[MonitorConfig] = field(default_factory=list)
    oracles: List[OracleConfig] = field(default_factory=list)
    time_guard: TimeGuardConfig = field(default_factory=TimeGuardConfig)
    data_setup: DataSetupConfig = field(default_factory=DataSetupConfig)
    policy_setup: PolicySetupConfig = field(default_factory=PolicySetupConfig)
    
    # Benchmark-specific config
    synthetic_config: Optional[SyntheticBenchmarkConfig] = None
    case_study_config: Optional[CaseStudyBenchmarkConfig] = None
    
    # Execution
    tools_to_build: List[str] = field(default_factory=list)
    oracle: OracleExecutionConfig = field(default_factory=OracleExecutionConfig)


@dataclass
class ExperimentSuiteEntry:
    """Single experiment entry in a suite"""
    path: str = MISSING
    enabled: bool = True
    description: str = ""


@dataclass
class ExperimentSuiteConfig:
    """Configuration for experiment suite"""
    experiments: List[ExperimentSuiteEntry] = field(default_factory=list)
