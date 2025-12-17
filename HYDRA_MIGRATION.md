# Migration to Hydra Configuration Framework

## Overview

The MonitoringFace CLI has been refactored to use **[Hydra](https://hydra.cc/)**, a powerful configuration framework from Facebook Research. This replaces the custom YAML parser with a standard, well-maintained library that provides better features and maintainability.

## What is Hydra?

Hydra is a framework for elegantly configuring complex applications. Key benefits include:

- **Structured Configs**: Type-safe configurations using Python dataclasses
- **Automatic Validation**: Configuration errors caught early with clear messages
- **Composition**: Easy override of specific values
- **Standard Library**: Well-documented, actively maintained by Facebook Research
- **OmegaConf**: Powerful YAML processing with variable interpolation and merging

## What Changed?

### 1. Dependencies
**Before:**
```python
pyyaml==6.0.1
```

**After:**
```python
hydra-core==1.3.2
omegaconf==2.3.0
```

### 2. Configuration Structure
The YAML structure has been slightly modified to work with Hydra's structured configs:

**Before:**
```yaml
data_setup:
  type: Signature
  config:
    trace_length: 1000
    event_rate: 1000
```

**After (Hydra-style):**
```yaml
data_setup:
  type: Signature
  Signature:
    trace_length: 1000
    event_rate: 1000
```

This allows Hydra to properly validate configurations against the structured config dataclasses.

### 3. New Files

#### `Infrastructure/Parser/HydraConfig.py`
Defines structured configuration dataclasses that match the YAML schema:
- `ExperimentConfig` - Main experiment configuration
- `ToolConfig`, `MonitorConfig`, `OracleConfig` - Component configs
- `SignatureDataConfig`, `PatternsDataConfig`, `DataGolfDataConfig` - Data setup configs
- And more...

These dataclasses provide:
- Type hints for all fields
- Default values
- Automatic validation
- IDE autocomplete support

#### Updated `Infrastructure/Parser/YamlParser.py`
Refactored to use Hydra's API:
- Uses `hydra.compose()` instead of `yaml.safe_load()`
- Works with `OmegaConf.DictConfig` objects
- Converts configs to internal data structures
- Cleaner code with less manual validation

### 4. CLI Remains the Same
The CLI interface is **unchanged**:
```bash
python -m Infrastructure.main experiments/example_synthetic_experiment.yaml
```

All command-line options work exactly as before.

## Benefits

### 1. Type Safety
Configurations are validated against dataclass definitions:
```python
@dataclass
class ToolConfig:
    name: str = MISSING  # Required field
    branch: str = MISSING  # Required field
    release: str = "branch"  # Optional with default
```

Missing required fields or wrong types are caught immediately.

### 2. Better Error Messages
**Before (custom parser):**
```
KeyError: 'config'
```

**After (Hydra):**
```
Missing mandatory value: tools[0].name
    full_key: tools[0].name
```

### 3. Less Code to Maintain
- ~400 lines of custom parsing logic replaced with ~200 lines using Hydra
- Standard library means bug fixes and features come automatically
- Well-documented API

### 4. IDE Support
With structured configs, IDEs can provide:
- Autocomplete for configuration fields
- Type checking
- Documentation tooltips

### 5. Future Extensibility
Hydra provides advanced features we can leverage:
- **Config composition**: Combine multiple config files
- **Config groups**: Organize configs by category
- **Command-line overrides**: Override any config value from CLI
- **Multi-run**: Run experiments with parameter sweeps
- **Plugins**: Extend Hydra with custom functionality

## Migration Guide for Users

### If You Have Existing YAML Files

Update the `data_setup` structure from:
```yaml
data_setup:
  type: Signature
  config:
    trace_length: 1000
```

To:
```yaml
data_setup:
  type: Signature
  Signature:
    trace_length: 1000
```

Similarly for `Patterns` and `DataGolfContract`.

Also update `policy_setup` to remove the nested `config:` key - fields go directly under `policy_setup`.

### New Files Work Out of the Box

All example files have been updated:
- `example_synthetic_experiment.yaml`
- `example_patterns.yaml`
- `example_case_study.yaml`
- `experiments_suite.yaml`

You can copy these as templates.

## Advanced Hydra Features (Optional)

### Command-Line Overrides

Override any config value directly from CLI:
```bash
python -m Infrastructure.main experiments/my_exp.yaml \
    experiment_name=custom_name \
    data_setup.Signature.trace_length=2000 \
    tools_to_build=[MonPoly,WhyMon]
```

### Config Composition (Future)

Organize configs into reusable components:
```
conf/
  experiment/
    base.yaml
    quick_test.yaml
  monitor/
    timelymon.yaml
    monpoly.yaml
```

Then compose them:
```bash
python -m Infrastructure.main +experiment=quick_test +monitor=timelymon
```

### Multi-Run (Future)

Run parameter sweeps:
```bash
python -m Infrastructure.main experiments/my_exp.yaml \
    --multirun \
    data_setup.Signature.trace_length=1000,2000,5000 \
    monitors.worker=1,4,8
```

## For Developers

### Adding New Configuration Options

1. **Update the structured config** in `HydraConfig.py`:
```python
@dataclass
class ExperimentConfig:
    # Add new field
    new_field: str = "default_value"
```

2. **Use in parser** (usually automatic):
```python
# Hydra automatically validates and provides the field
new_value = self.cfg.new_field
```

3. **Update documentation** with examples

### Why Not Use @hydra.main?

We use Hydra's Compose API (`compose()`) instead of the `@hydra.main` decorator because:
- We need to load configs dynamically based on file paths
- We want control over working directory
- We support both single experiments and experiment suites
- CLI interface is already established

## Resources

- [Hydra Documentation](https://hydra.cc/)
- [OmegaConf Documentation](https://omegaconf.readthedocs.io/)
- [Structured Configs Tutorial](https://hydra.cc/docs/tutorials/structured_config/intro/)
- [Hydra GitHub](https://github.com/facebookresearch/hydra)

## Compatibility

- Python 3.7+
- All existing CLI commands work unchanged
- Backward compatible with proper YAML migration
- No changes to internal data structures

## Questions?

See `CLI_USAGE.md` for complete documentation or open an issue on GitHub.
