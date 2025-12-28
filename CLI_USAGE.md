# MonitoringFace CLI Documentation

## Overview

MonitoringFace provides a command-line interface (CLI) that allows users to configure and run benchmark experiments using YAML configuration files. The framework uses **[Hydra](https://hydra.cc/)**, a powerful configuration framework that provides structured configs, type safety, and automatic validation.

## Key Benefits of Hydra Integration

- **Type Safety**: Structured configs with dataclasses ensure type correctness
- **Automatic Validation**: Configuration errors are caught early with clear error messages
- **Composability**: Easy to override specific configuration values
- **Clean Syntax**: Natural YAML structure without excessive nesting

## Installation

1. Install dependencies (includes hydra-core and omegaconf):
```bash
cd Infrastructure
pip install -r requirements.txt
```

2. Ensure Docker is running (required for building and running monitoring tools)

## Quick Start

### Running a Single Experiment

```bash
python -m Infrastructure.main example_synthetic_experiment.yaml
```

### Running Multiple Experiments (Suite)

```bash
python -m Infrastructure.main experiments_suite.yaml
```

### Validating Configuration (Dry Run)

```bash
python -m Infrastructure.main example_synthetic_experiment.yaml --dry-run
```

## Command-Line Options

```
usage: MonitoringFace [-h] [--build-dir BUILD_DIR] [--exp-dir EXP_DIR] 
                      [--dry-run] [--verbose] [--suite] config

positional arguments:
  config                Path to YAML configuration file (single experiment or suite)

optional arguments:
  -h, --help           Show help message and exit
  --dry-run            Validate configuration without running experiments
  --verbose, -v        Enable verbose output
  --suite              Force treat config as experiment suite (auto-detected by default)
```

## YAML Configuration Format

### Single Experiment Configuration

A single experiment YAML file contains all the information needed to run one benchmark experiment.

#### Required Sections

##### 1. Experiment Metadata
```yaml
experiment_name: my_experiment  # Unique name for the experiment
benchmark_type: synthetic       # 'synthetic' or 'case_study'
```

##### 2. Tools Configuration
Define which monitoring tools to build:
```yaml
tools:
  - name: TimelyMon
    branch: development
    release: branch              # 'branch' or 'release'
  - name: MonPoly
    branch: master
    release: branch
```

##### 3. Monitors Configuration
Configure monitors to run during the experiment:
```yaml
monitors:
  - identifier: TimelyMon        # Tool identifier
    name: TimelyMon 1            # Unique monitor name
    branch: development          # Git branch
    params:                      # Monitor-specific parameters
      worker: 1
      output_mode: 1
  - identifier: MonPoly
    name: MonPoly
    branch: master
    params:
      replayer: gen_data
```

##### 4. Time Guard Configuration
Configure execution time limits:
```yaml
time_guard:
  enabled: false                 # Enable/disable time guarding
  lower_bound: null              # Minimum time (null for none)
  upper_bound: 200               # Maximum time in seconds
  guard_type: Monitor            # 'Monitor', 'Oracle', or 'Generator'
  guard_name: TimelyMon 6        # Name of guard monitor
```

##### 5. Data Setup Configuration
Configure data generation. With Hydra, configuration is organized by type:

**Signature Generator:**
```yaml
data_setup:
  type: Signature
  Signature:
    trace_length: 1000
    seed: null
    event_rate: 1000
    index_rate: null
    time_stamp: null
    sig: ""
    sample_queue: null
    string_length: null
    fresh_value_rate: null
    domain: null
```

**Patterns Generator:**
```yaml
data_setup:
  type: Patterns
  Patterns:
    trace_length: 1000
    seed: null
    event_rate: 1000
    index_rate: null
    time_stamp: null
    linear: 1
    interval: null
    star: null
    triangle: null
    pattern: null
    violations: 1.0
    zipf: "x=1.5+3,z=2"
    prob_a: 0.2
    prob_b: 0.3
    prob_c: 0.5
```

**DataGolf Contract:**
```yaml
data_setup:
  type: DataGolfContract
  DataGolfContract:
    sig_file: "signature.sig"
    formula: "formula.mfotl"
    tup_ts: [0, 1, 2, 3, 4, 5, 6]
    tup_amt: 100
    tup_val: 1
    oracle: true
    no_rewrite: null
    trace_length: 5
```

##### 6. Policy Setup Configuration
```yaml
policy_setup:
  type: PolicyGeneratorContract
  num_preds: 4
  prob_eand: 0
  prob_rand: 0
  prob_let: 0
  prob_matchF: 0
  prob_matchP: 0
```

##### 7. Benchmark-Specific Configuration

**For Synthetic Benchmarks:**
```yaml
synthetic_config:
  data_source: DATAGENERATOR     # 'DATAGENERATOR' or 'DATAGOLF'
  policy_source: MFOTLGENERATOR  # 'MFOTLGENERATOR' or 'PATTERNS'
  experiment:
    num_operators: [5]
    num_fvs: [2]
    num_setting: [0, 1]
    num_data_set_sizes: [50]
```

**For Case Studies:**
```yaml
case_study_config:
  case_study_name: Nokia
```

##### 8. Execution Configuration
```yaml
experiment_type: Signature       # 'Pattern', 'Signature', or 'CaseStudy'

tools_to_build:                  # List of monitor names to run
  - TimelyMon 1
  - MonPoly
  - VeriMon
```

##### 9. Oracle Configuration (Optional)
```yaml
oracles:
  - identifier: VeriMonOracle
    name: VeriMonOracle
    monitor_name: VeriMon
    params:
      replayer: gen_data
      verified: true

oracle:
  enabled: true
  name: VeriMonOracle
```

### Experiment Suite Configuration

An experiment suite YAML file references multiple individual experiment configurations:

```yaml
experiments:
  - path: example_synthetic_experiment.yaml
    enabled: true
    description: "Basic synthetic experiment"
  
  - path: example_patterns.yaml
    enabled: true
    description: "Patterns data generator experiment"
  
  - path: example_case_study.yaml
    enabled: false                # Can be disabled without removing
    description: "Nokia case study"
```

**Note:** Paths can be relative (to the suite file) or absolute.

## Complete Examples

### Example 1: Basic Synthetic Experiment

See: `Archive/Benchmarks/example_synthetic_experiment.yaml`

This example demonstrates a complete synthetic benchmark with:
- Multiple monitors (TimelyMon, MonPoly, WhyMon, EnfGuard)
- Signature data generator
- VeriMon oracle for correctness checking
- Time guarding enabled

### Example 2: Patterns Generator

See: `Archive/Benchmarks/example_patterns.yaml`

This example shows:
- Using the Patterns data generator
- Multiple parameter sweeps
- Simplified monitor configuration

### Example 3: Case Study

See: `Archive/Benchmarks/example_case_study.yaml`

This example demonstrates:
- Case study benchmark (Nokia)
- Minimal monitor setup
- No oracle required

### Example 4: Experiment Suite

See: `Archive/Benchmarks/experiments_suite.yaml`

This example shows how to:
- Group multiple experiments
- Enable/disable experiments
- Add descriptions for documentation

## Usage Patterns

### 1. Create a New Experiment

1. Copy an existing example YAML file:
```bash
cp Archive/Benchmarks/example_synthetic_experiment.yaml \
   Archive/Benchmarks/my_experiment.yaml
```

2. Edit the configuration to match your needs

3. Validate the configuration:
```bash
python -m Infrastructure.main my_experiment.yaml --dry-run
```

4. Run the experiment:
```bash
python -m Infrastructure.main my_experiment.yaml --verbose
```

### 2. Create an Experiment Suite

1. Create individual experiment YAML files

2. Create a suite file:
```yaml
experiments:
  - path: experiment1.yaml
    enabled: true
    description: "First experiment"
  - path: experiment2.yaml
    enabled: true
    description: "Second experiment"
```

3. Run the suite:
```bash
python -m Infrastructure.main my_suite.yaml
```

### 3. Parameter Sweeps

Use lists in the synthetic experiment configuration to run multiple variations:

```yaml
synthetic_config:
  experiment:
    num_operators: [3, 5, 7, 10]      # Will run 4 variations
    num_fvs: [1, 2, 3]                # Combined with above
    num_data_set_sizes: [50, 100, 500]
```

This will generate experiments for all combinations of parameters.

### 4. Organizing Experiments

Recommended directory structure:

```
Archive/Benchmarks/
├── experiments_suite.yaml          # Main suite file
├── synthetic/
│   ├── basic_experiment.yaml
│   ├── scaling_test.yaml
│   └── correctness_test.yaml
├── case_studies/
│   ├── nokia.yaml
│   └── other_case_study.yaml
└── ablation/
    ├── no_optimization.yaml
    └── with_optimization.yaml
```

## Advanced Features

### Verbose Output

Get detailed information during execution:

```bash
python -m Infrastructure.main my_experiment.yaml --verbose
```

### Programmatic Usage

You can also use the CLI programmatically in Python:

```python
from Infrastructure.cli import CLI

cli = CLI()
cli.run(['experiments/my_experiment.yaml', '--verbose'])
```

### Using the YAML Parser Directly

For more control, use the parser directly:

```python
from Infrastructure.Parser.YamlParser import YamlParser

parser = YamlParser('my_experiment.yaml')
experiment_config = parser.parse_experiment()

# Access parsed components
tool_manager = experiment_config['tool_manager']
monitor_manager = experiment_config['monitor_manager']
# ... etc
```

## Troubleshooting

### Common Issues

**1. Docker not running:**
```
Error: Docker is not running
```
Solution: Start Docker before running experiments

**2. YAML syntax error:**
```
Error parsing YAML file: ...
```
Solution: Validate YAML syntax using an online validator or `python -c "import yaml; yaml.safe_load(open('file.yaml'))"`

**3. Configuration validation error:**
```
Configuration error: Missing 'tools' section in YAML configuration
```
Solution: Ensure all required sections are present in your YAML file

**4. Module import error:**
```
Import "omegaconf" could not be resolved
```
Solution: Install dependencies: `pip install -r requirements.txt`

**5. Experiment file not found:**
```
Experiment file not found: ...
```
Solution: Check that paths in suite files are correct (relative or absolute)

### Debug Mode

Enable verbose output to see detailed execution information:

```bash
python -m Infrastructure.main my_experiment.yaml --verbose
```

### Validate Before Running

Always validate configuration before running expensive experiments:

```bash
python -m Infrastructure.main my_experiment.yaml --dry-run
```

## Migration from Hardcoded Configuration

To migrate from the old `Evaluator.py` approach:

1. Identify your current configuration in `Evaluator.py`
2. Copy an appropriate example YAML file
3. Transfer your configuration values to the YAML file
4. Validate with `--dry-run`
5. Run the experiment using the CLI

## Additional Resources

- [Hydra Documentation](https://hydra.cc/) - Learn more about Hydra's powerful configuration features
- [OmegaConf Documentation](https://omegaconf.readthedocs.io/) - Learn about OmegaConf's structured configs
- See example YAML files in `Archive/Benchmarks/`
- Review `Infrastructure/Parser/YamlParser.py` for all configuration options
- Review `Infrastructure/Parser/HydraConfig.py` for structured config definitions
- Check `Infrastructure/cli.py` for CLI implementation details

## Contributing

When adding new configuration options:

1. Update the structured config dataclass in `HydraConfig.py`
2. Add parsing logic in `YamlParser.py` if needed
3. Update this documentation with examples
4. Add example configurations to `Archive/Benchmarks/` directory

The use of Hydra means most configuration changes only require updating the dataclass definitions.
