# Infrastructure — the platform core

The **Infrastructure** is the part of MonitoringFace provided and maintained by the
platform. It supplies the **abstract base classes** for the six component types and
the platform-level services shared by every experiment: the CLI/frontend, the
orchestrator that resolves dependencies and drives execution, the format converters,
and the evaluation logic for timing, memory, and correctness checking.

Concrete components are *not* added here — they live in the
[Archive](../Archive/README.md) as a Dockerfile plus a Python wrapper class that
extends one of the base classes below. This document explains those base classes and
how to integrate a new component against them.

## Base classes at a glance

| Component | Base class | Location |
|-----------|-----------|----------|
| Monitor | `BaseMonitorTemplate` | [`Monitors/BaseMonitorTemplate.py`](Monitors/BaseMonitorTemplate.py) |
| Data generator | `DataGeneratorTemplate` | [`Builders/ProcessorBuilder/DataGenerators/DataGeneratorTemplate.py`](Builders/ProcessorBuilder/DataGenerators/DataGeneratorTemplate.py) |
| Policy generator | `PolicyGeneratorTemplate` | [`Builders/ProcessorBuilder/PolicyGenerators/PolicyGeneratorTemplate.py`](Builders/ProcessorBuilder/PolicyGenerators/PolicyGeneratorTemplate.py) |
| Oracle | `AbstractOracleTemplate` | [`Oracles/AbstractOracleTemplate.py`](Oracles/AbstractOracleTemplate.py) |
| Data converter | `DataConverterTemplate` | [`Builders/ProcessorBuilder/DataConverters/DataConverterTemplate.py`](Builders/ProcessorBuilder/DataConverters/DataConverterTemplate.py) |
| Policy converter | `PolicyConverterTemplate` | [`Builders/ProcessorBuilder/PolicyConverters/PolicyConverterTemplate.py`](Builders/ProcessorBuilder/PolicyConverters/PolicyConverterTemplate.py) |
| Case study | `CaseStudyTemplate` | [`Builders/ProcessorBuilder/CaseStudiesGenerators/CaseStudyTemplate.py`](Builders/ProcessorBuilder/CaseStudiesGenerators/CaseStudyTemplate.py) |
| Contract | `AbstractContract` | [`DataTypes/Contracts/AbstractContract.py`](DataTypes/Contracts/AbstractContract.py) |

The design standardizes only the interface that components expose to the automation.
Monitors, oracles, and generators are exposed to the automation and therefore must
follow these conventions; converters are *not* directly exposed and may take arbitrary
parameters and produce custom outputs (it is assumed the consuming stage knows how to
handle them).

## Authentication token

To avoid rate limiting when pulling images and metadata from GitHub, add a personal
access token. Create the folder `Infrastructure/environment/` and add a file named
`auth_token` containing your token.

## Adding a component

In every case the recipe is the same: package the third-party software as a Dockerfile
under `Archive/Docker/<Category>/` (see the [Archive README](../Archive/README.md) for
Dockerfile and `tool.properties` conventions), then add a wrapper class under
`Archive/Implementations/...` that extends the corresponding base class. For automatic
discovery the folder, file, and class names must match.

### Monitor

Extend **`BaseMonitorTemplate`**. A monitor connects to its Docker image and declares
the trace/policy formats it accepts (`supported_trace_formats`,
`supported_policy_formats`); for those formats the platform performs automatic
conversion. Override `preprocessing_data` / `preprocessing_policy` for custom
pre-processing, and implement the **offline** and/or **online** running interface
(`construct_offline_command` / `construct_online_command`, optional `*_compile`, and a
`post_processing_*` method that emits one of the platform's verdict formats). See
**[Monitors/README.md](Monitors/README.md)** for the full method-level guide.

### Data and policy generators

Generators are tightly integrated with the automation and must adhere strictly to their
interfaces. A **data generator** extends `DataGeneratorTemplate` and implements
`run_generator` (build the command, return the seed and generated data), `check_policy`
(reject incompatible policies; return `True` if it accepts all), and `output_format`. A
**policy generator** extends `PolicyGeneratorTemplate` and implements `generate_policy`
and `output_format`. See
**[Builders/ProcessorBuilder/README.md](Builders/ProcessorBuilder/README.md)** for the
step-by-step guide, including how to define the accompanying contract.

### Oracle

An oracle may be a monitor or a custom tool. Extend **`AbstractOracleTemplate`** and
implement `pre_process_data`, `compute_result`, and `post_process_data` to produce and
store the ground truth, plus a `verify` method that compares a tool's output against
that ground truth to yield a correctness verdict. The VeriMon-based oracle reuses a
monitor by composition (pre-/post-processing and running), implementing only `verify`;
the Data Golf-based oracle obtains the ground truth from the generator and likewise
implements only `verify`.

### Converters

Converters transform trace or policy formats. Integrating them into the automation is
*optional* — a converter can also be invoked directly inside a monitor wrapper's
pre-processing. To register one, extend `DataConverterTemplate` or
`PolicyConverterTemplate` and implement `conversion_scheme` (the pairs of formats it
maps between) and the conversion methods (`convert` / `auto_convert`).

### Case studies

A case study is contributed as a YAML configuration plus its static data (see the
[Archive README](../Archive/README.md#case-studies)). Programmatic case-study
generators extend `CaseStudyTemplate` and implement `run_generator`.

### Contracts

A **contract** is a dataclass describing a component's configuration options (e.g.
trace length and event frequencies for a trace generator, or formula size and operator
frequencies for a policy generator). Extend `AbstractContract` and implement:

- `default_contract()` — populate all fields with reasonable defaults.
- `instantiate_contract(params)` — populate fields from the supplied `params`
  dictionary, falling back to `default_contract()` when `params` is empty.

## Utilities and converters

Beyond the conventions above, there are no additional requirements for implementing
utilities and converters — keep them general and well-behaved so they remain reusable.
