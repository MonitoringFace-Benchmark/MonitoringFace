# Data and Policy Generators

A **generator** produces experiment inputs — *data generators* produce traces, *policy
generators* produce policies — subject to parameters carried by a **contract**. This
document describes how to add one. The base classes live here in the Infrastructure;
the concrete generators live in the [Archive](../../../Archive/README.md).

## Where a generator lives

Each generator consists of:

- a **Dockerfile** packaging the generator, under
  `Archive/Docker/DataGenerators/<Name>Generator/` or
  `Archive/Docker/PolicyGenerators/<Name>Generator/`
  (see the [Archive README](../../../Archive/README.md)), and
- a **wrapper class + contract**, under
  `Archive/Implementations/Builders/ProcessorBuilder/<DataGenerators|PolicyGenerators>/<Name>Generator/`.

> Note: generators are **added to the Archive**, not to the Infrastructure. The
> Infrastructure only holds the base classes (`DataGeneratorTemplate`,
> `PolicyGeneratorTemplate`, `AbstractContract`) that the Archive classes extend.

## Common structure

Create a folder named `<Name>Generator` (camel-case, ending in `Generator`) containing:

```
<Name>Generator/
  __init__.py
  <Name>Generator.py    → class <Name>Generator(DataGeneratorTemplate | PolicyGeneratorTemplate)
  <Name>Contract.py     → class <Name>Contract(AbstractContract)
```

### Discovery and naming

The platform derives the generator from the contract by replacing `Contract` with
`Generator`. Therefore the names must line up exactly:

- The YAML `data_setup.type` / `policy_setup.type` equals the **contract** class name,
  e.g. `SignatureContract`.
- The folder, file, and **generator** class name must all be `<Name>Generator`,
  e.g. `SignatureGenerator`.

So `type: SignatureContract` ⇒ the platform loads
`.../DataGenerators/SignatureGenerator/SignatureGenerator.py` and reads the contract
fields from the YAML block named `SignatureContract`.

## The contract

Define a dataclass `<Name>Contract` that extends `AbstractContract`
([`Infrastructure/DataTypes/Contracts/AbstractContract.py`](../../DataTypes/Contracts/AbstractContract.py)).
Each dataclass field is one tunable parameter/option of the generator. Implement:

1. **`default_contract(self)`** — return an instance with reasonable default values.
2. **`instantiate_contract(self, params)`** — set fields from the `params` dict (a raw
   dict parsed from YAML); fall back to `default_contract()` when `params` is empty.

```python
from dataclasses import dataclass
from Infrastructure.DataTypes.Contracts.AbstractContract import AbstractContract

@dataclass
class SignatureContract(AbstractContract):
    trace_length: int = None
    event_rate: int = 1000
    seed: int = None
    # ...

    def default_contract(self):
        return SignatureContract(trace_length=None, event_rate=1000, seed=None)

    def instantiate_contract(self, params):
        if not params:
            return self.default_contract()
        valid = {f.name for f in fields(self)}
        for k, v in params.items():
            if k in valid:
                setattr(self, k, v)
        return self
```

## Data generators

Extend `DataGeneratorTemplate`
([`DataGenerators/DataGeneratorTemplate.py`](DataGenerators/DataGeneratorTemplate.py))
and implement:

1. **`__init__(self, name, path_to_build)`** — links the class to its Docker image.
2. **`run_generator(self, contract_inner: Dict[AnyStr, Any], time_on=None, time_out=None) -> Tuple[int, AnyStr]`**
   Execute the generator with the (raw dict) contract; build and run the image command.
   `time_on`/`time_out` are supplied by the framework for time-guarded generation and
   must be passed through to the image call. Return `(seed, generated_trace)`.
3. **`check_policy(self, path_inner, signature, formula) -> bool`**
   Validate that the given policy is compatible with this generator (return `True` if
   it accepts any policy; e.g. `SignatureGenerator` accepts all).
4. **`output_format() -> InputOutputTraceFormats`** (static) — the trace format produced.

## Policy generators

Extend `PolicyGeneratorTemplate`
([`PolicyGenerators/PolicyGeneratorTemplate.py`](PolicyGenerators/PolicyGeneratorTemplate.py))
and implement:

1. **`__init__(self, name, path_to_build)`** — links the class to its Docker image.
2. **`generate_policy(self, policy_contract: Dict[AnyStr, Any], time_on=None, time_out=None) -> Tuple[int, AnyStr, AnyStr]`**
   Parse the (raw dict) contract into the image command, run it, and return
   `(seed, signature, policy)`. Pass `time_on`/`time_out` through to the image call.
3. **`output_format() -> InputOutputPolicyFormats`** (static) — the policy format produced.

## See also

- [Archive README](../../../Archive/README.md) — Dockerfile and `tool.properties` conventions for the generator image.
- [CLI Usage Guide](../../Frontend/CLI/CLI_USAGE.md) — how contracts appear in experiment YAML, with a per-contract field reference.
- [Infrastructure README](../../README.md) — the other component base classes.
