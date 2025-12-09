# MonitoringFace CLI - Quick Reference

**Using Hydra for Configuration Management**

## Installation
```bash
cd Infrastructure
pip install -r requirements.txt  # Includes hydra-core and omegaconf
```

## Basic Usage

### Run single experiment
```bash
python -m Infrastructure.main experiments/example_synthetic_experiment.yaml
```

### Run experiment suite
```bash
python -m Infrastructure.main experiments/experiments_suite.yaml
```

### Validate configuration
```bash
python -m Infrastructure.main experiments/my_experiment.yaml --dry-run
```

### Verbose output
```bash
python -m Infrastructure.main experiments/my_experiment.yaml --verbose
```

## YAML Structure Quick Reference

### Minimal Synthetic Experiment
```yaml
experiment_name: my_experiment
benchmark_type: synthetic

tools:
  - name: MonPoly
    branch: master
    release: branch

monitors:
  - identifier: MonPoly
    name: MonPoly
    branch: master
    params:
      replayer: gen_data

time_guard:
  enabled: false
  upper_bound: 200
  guard_type: Monitor
  guard_name: MonPoly

# Hydra structured format - note the nested structure
data_setup:
  type: Signature
  Signature:
    trace_length: 1000
    event_rate: 1000

policy_setup:
  type: PolicyGeneratorContract
  num_preds: 4

synthetic_config:
  data_source: DATAGENERATOR
  policy_source: MFOTLGENERATOR
  experiment:
    num_operators: [5]
    num_fvs: [2]
    num_setting: [0]
    num_data_set_sizes: [50]

experiment_type: Signature
tools_to_build:
  - MonPoly

oracle:
  enabled: false
```

### Minimal Case Study
```yaml
experiment_name: nokia_case
benchmark_type: case_study

tools:
  - name: MonPoly
    branch: master
    release: branch

monitors:
  - identifier: MonPoly
    name: MonPoly
    branch: master
    params:
      replayer: gen_data

time_guard:
  enabled: false

case_study_config:
  case_study_name: Nokia

# Hydra structured format
data_setup:
  type: Signature
  Signature:
    trace_length: 1000

experiment_type: CaseStudy
tools_to_build:
  - MonPoly

oracle:
  enabled: false
```

### Experiment Suite
```yaml
experiments:
  - path: experiments/exp1.yaml
    enabled: true
    description: "First experiment"
  - path: experiments/exp2.yaml
    enabled: true
    description: "Second experiment"
```

## Configuration Options

### benchmark_type
- `synthetic`: Synthetic benchmark
- `case_study`: Case study benchmark

### data_setup.type
- `Signature`: Signature-based data generator
- `Patterns`: Pattern-based data generator
- `DataGolfContract`: DataGolf-based generator

### experiment_type
- `Pattern`
- `Signature`
- `CaseStudy`

### synthetic_config.data_source
- `DATAGENERATOR`
- `DATAGOLF`

### synthetic_config.policy_source
- `MFOTLGENERATOR`
- `PATTERNS`

### time_guard.guard_type
- `Monitor`
- `Oracle`
- `Generator`

### tools/monitors: release
- `branch`: Use Git branch
- `release`: Use release version

## Common Monitor Identifiers
- `TimelyMon`
- `MonPoly`
- `WhyMon`
- `EnfGuard`

## Common Oracle Identifiers
- `VeriMonOracle`
- `DataGolfOracle`

## Examples Location
- Single experiments: `Infrastructure/experiments/example_*.yaml`
- Suite: `Infrastructure/experiments/experiments_suite.yaml`

## Tips
- Framework uses **Hydra** for configuration management
- Configuration is type-safe with structured configs (see `HydraConfig.py`)
- Use `--dry-run` to validate before running
- Use `--verbose` for debugging
- Use `null` in YAML for None/null values
- Paths in suite files can be relative or absolute
- Disable experiments in suites with `enabled: false`
- Data setup uses nested structure: `type: Signature` with `Signature: {...}` config

## Full Documentation
- See `CLI_USAGE.md` for complete documentation
- [Hydra Documentation](https://hydra.cc/) for advanced configuration features
