# MonitoringFace Benchmark Framework

MonitoringFace is a comprehensive benchmark framework for evaluating runtime monitoring tools and techniques. It uses **Hydra** for powerful, type-safe YAML configuration management.

## Quick Start

### Installation

```bash
cd Infrastructure
pip install -r requirements.txt
```

Ensure Docker is running before executing experiments.

### Running Experiments

The framework uses Hydra-powered YAML configuration for experiments:

```bash
# Run a single experiment
python -m Infrastructure.main experiments/example_synthetic_experiment.yaml

# Run a suite of experiments
python -m Infrastructure.main experiments/experiments_suite.yaml

# Validate configuration without running
python -m Infrastructure.main experiments/my_experiment.yaml --dry-run
```

### Documentation

- **[CLI Usage Guide](CLI_USAGE.md)** - Complete documentation for the command-line interface and YAML configuration
- **[Quick Reference](CLI_QUICK_REFERENCE.md)** - Quick reference for common commands and configuration options
- **[Archive README](Archive/README.md)** - How to add Dockerfiles for new tools
- **[Infrastructure README](Infrastructure/README.md)** - How to integrate new software components

## Key Features

- **Hydra Configuration**: Leverages [Hydra](https://hydra.cc/) for powerful, type-safe YAML configuration with structured configs
- **YAML-based Experiments**: Define experiments using simple, version-controlled YAML files
- **Experiment Suites**: Run multiple experiments in sequence from a single suite file
- **Flexible Monitoring**: Support for multiple monitoring tools (TimelyMon, MonPoly, WhyMon, EnfGuard)
- **Data Generators**: Multiple data generation strategies (Signature, Patterns, DataGolf)
- **Oracle Support**: Correctness verification using oracles (VeriMon, DataGolf)
- **Time Guards**: Configurable execution time limits
- **Dry Run Mode**: Validate configurations before execution
- **Configuration Validation**: Hydra's OmegaConf provides runtime type checking

## Project Structure

```
MonitoringFace/
├── Infrastructure/           # Main framework code
│   ├── main.py              # CLI entry point
│   ├── cli.py               # Command-line interface
│   ├── requirements.txt     # Python dependencies
│   ├── Parser/              # Configuration parsing
│   │   └── YamlParser.py   # YAML parser for experiments
│   ├── experiments/         # Example experiment configurations
│   │   ├── example_synthetic_experiment.yaml
│   │   ├── example_patterns.yaml
│   │   ├── example_case_study.yaml
│   │   └── experiments_suite.yaml
│   ├── BenchmarkBuilder/    # Benchmark construction
│   ├── Monitors/            # Monitor implementations
│   ├── Oracles/             # Oracle implementations
│   └── ...
├── Archive/                 # Tool Dockerfiles and configurations
├── CLI_USAGE.md            # Complete CLI documentation
└── CLI_QUICK_REFERENCE.md  # Quick reference guide
```

## Example Workflow

### 1. Create an Experiment Configuration

Create a YAML file (e.g., `my_experiment.yaml`):

```yaml
experiment_name: my_test
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

data_setup:
  type: Signature
  config:
    trace_length: 1000
    event_rate: 1000

policy_setup:
  type: PolicyGeneratorContract
  config:
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

time_guard:
  enabled: false
```

### 2. Validate and Run

```bash
# Validate configuration
python -m Infrastructure.main my_experiment.yaml --dry-run

# Run experiment
python -m Infrastructure.main my_experiment.yaml --verbose
```

## Configuration Options

### Benchmark Types
- **Synthetic**: Automatically generated benchmarks with configurable parameters
- **Case Study**: Real-world case studies (e.g., Nokia)

### Data Generators
- **Signature**: Generate traces based on signature specifications
- **Patterns**: Generate traces with specific patterns (linear, star, triangle)
- **DataGolf**: Use DataGolf-based generation

### Monitoring Tools
- TimelyMon
- MonPoly
- WhyMon
- EnfGuard

### Oracles
- VeriMonOracle (based on verified MonPoly)
- DataGolfOracle

## Advanced Usage

### Multiple Experiments (Suite)

Create a suite file `experiments_suite.yaml`:

```yaml
experiments:
  - path: experiments/exp1.yaml
    enabled: true
    description: "Baseline experiment"
  - path: experiments/exp2.yaml
    enabled: true
    description: "Scaling test"
  - path: experiments/exp3.yaml
    enabled: false  # Temporarily disabled
    description: "Optional experiment"
```

Run the suite:
```bash
python -m Infrastructure.main experiments_suite.yaml
```

### Parameter Sweeps

Use lists to run experiments with different parameters:

```yaml
synthetic_config:
  experiment:
    num_operators: [3, 5, 7, 10]     # Test multiple operator counts
    num_fvs: [1, 2, 3]                # Test different free variables
    num_data_set_sizes: [50, 100, 500]
```

### Custom Directories

```bash
python -m Infrastructure.main my_experiment.yaml \
    --build-dir /path/to/build \
    --exp-dir /path/to/experiments
```

## Migration from Old Format

If you have experiments in the old `Evaluator.py` format, you can convert them to YAML:

1. Identify your configuration in `Evaluator.py`
2. Use the example YAML files as templates
3. Transfer configuration values to YAML
4. Validate with `--dry-run`
5. Run with the new CLI

See the `Infrastructure/Parser/ParserComponents.py` file for programmatic conversion between formats.

## Contributing

### Adding New Tools
See [Archive/README.md](Archive/README.md) for information on adding tool Dockerfiles.

### Adding New Features
See [Infrastructure/README.md](Infrastructure/README.md) for integration guidelines.

### Updating Configuration Schema
When adding new configuration options:
1. Update the relevant dataclass/contract
2. Add parsing logic in `YamlParser.py`
3. Update documentation in `CLI_USAGE.md`
4. Add example configurations

## Troubleshooting

**Docker not running:**
```
Error: Docker is not running
```
Start Docker before running experiments.

**YAML syntax errors:**
Use `--dry-run` to validate configuration before running:
```bash
python -m Infrastructure.main my_experiment.yaml --dry-run
```

**Missing dependencies:**
```bash
pip install -r Infrastructure/requirements.txt
```

For more troubleshooting tips, see [CLI_USAGE.md](CLI_USAGE.md#troubleshooting).

## License

[Add your license information here]

## Contact

[Add contact information here]
