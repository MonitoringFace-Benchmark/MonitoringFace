# MonitoringFace Benchmark Framework
MonitoringFace is a comprehensive benchmark framework for evaluating runtime monitoring tools and techniques.

## Prerequisites

Docker must be installed and running on your system. You can download Docker from
[here](https://www.docker.com/get-started).
Recommended/Minimum Docker system requirements:

    - RAM: 6GB
    - 4 CPU cores
    - Swap memory: 1GB
    - Disk space: 64GB
    - Allow Docker to access the folder where MonitoringFace is located under Settings> Resources > File Sharing.

Python 3.9 or higher must be installed. You can download Python from
[here](https://www.python.org/downloads/).

### Installation
Clone the repository and install dependencies:
```bash
$ python -m venv .venv
$ source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
(.venv) $ pip install -r Infrastructure/requirements.txt
```

### Running Experiments

Make sure Docker is running and that you have an internet connection.

The framework uses Hydra-powered YAML configuration for experiments:

```bash
# Run a single experiment
python -m Infrastructure.main examples/example_synthetic_experiment.yaml

# Run a suite of experiments
python -m Infrastructure.main examples/experiments_suite.yaml

# Validate configuration without running
python -m Infrastructure.main my_folder/my_experiment.yaml --dry-run
```

### Documentation

- **[CLI Usage Guide](Infrastructure/CLI/CLI_USAGE.md)** - Complete documentation for the command-line interface and YAML configuration
- **[Archive README](Archive/README.md)** - How to add Dockerfiles for new tools
- **[Infrastructure README](Infrastructure/README.md)** - How to integrate new software components

## Key Features

- **YAML-based Experiments**: Define experiments using simple, version-controlled YAML files
- **Experiment Suites**: Run multiple experiments in sequence from a single suite file
- **Flexible Monitoring**: Support for multiple monitoring tools (TimelyMon, MonPoly, WhyMon, EnfGuard)
- **Data Generators**: Multiple data generation strategies (Signature, Patterns, DataGolf)
- **Oracle Support**: Correctness verification using oracles (VeriMon, DataGolf)
- **Time Guards**: Configurable execution time limits
- **Dry Run Mode**: Validate configurations before execution

## Project Structure

```
MonitoringFace/
├── Infrastructure/           # Main framework code
│   ├── main.py              # CLI entry point
│   ├── cli.py               # Command-line interface
│   ├── requirements.txt     # Python dependencies
│   ├── Parser/              # Configuration parsing
│   │   └── YamlParser.py   # YAML parser for experiments
│   ├── BenchmarkBuilder/    # Benchmark construction
│   ├── Monitors/            # Monitor implementations
│   ├── Oracles/             # Oracle implementations
│   ├── Builders/            # Generator and Converter implementations
│   └── ...
├── Archive/                 # Tool Dockerfiles and configurations
│   ├── Benchmarks/         # Example experiment configurations
│   │   ├── examples
│   │   │   ├── example_synthetic_experiment.yaml
│   │   │   ├── example_patterns.yaml
│   │   │   ├── example_case_study.yaml
│   │   │   ├── experiments_suite.yaml
│   │   │   └── ...
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
python -m Infrastructure.main path/my_experiment.yaml --dry-run

# Run experiment
python -m Infrastructure.main path/my_experiment.yaml --verbose
```

### 3. Debugging
Run with `--debug` to store intermediate results and temporary files.
```bash
# Validate configuration
python -m Infrastructure.main path/my_experiment.yaml --debug

# Run experiment
python -m Infrastructure.main path/my_experiment.yaml --verbose --debug
```

### 4. Cleanup Results
Over time, experiment results accumulate. Use cleanup commands to manage storage:
```bash
# Clean up old results, keeping only the latest for each experiment
python -m Infrastructure.main --cleanup

# Preview what would be deleted without actually deleting
python -m Infrastructure.main --cleanup --dry-run

# Keep the 3 most recent results for each experiment
python -m Infrastructure.main --cleanup --keep 3

# Remove all results and experiment data (requires confirmation)
python -m Infrastructure.main --cleanup-all
```

## Configuration Options

### Benchmark Types
- **Synthetic**: Automatically generated benchmarks with configurable parameters
- **Case Study**: Real-world case studies (e.g., Nokia)

### Data Generators (examples)
- **Signature**: Generate traces based on signature specifications
- **Patterns**: Generate traces with specific patterns (linear, star, triangle)
- **DataGolf**: Use DataGolf-based generation

### Monitoring Tools (examples)
- TimelyMon
- MonPoly
- WhyMon
- EnfGuard

### Oracles (examples)
- VeriMonOracle (based on verified MonPoly aka. VeriMon)
- DataGolfOracle (based on DataGolf)


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
python -m Infrastructure.main my_folder/experiments_suite.yaml
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

## Contributing

### Adding New Tools
See [Archive/README.md](Archive/README.md) for information on adding tool Dockerfiles.

### Adding New Features
See [Infrastructure/README.md](Infrastructure/README.md) for integration guidelines.

### Updating Configuration Schema
When adding new configuration options:
1. Update the relevant dataclass/contract
2. Update documentation in `CLI_USAGE.md`
3. Add example configurations

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
python -m Infrastructure.main my_folder/my_experiment.yaml --dry-run
```
