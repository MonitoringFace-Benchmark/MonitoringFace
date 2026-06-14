# Archive — the community-contributed layer

The **Archive** is the layer of MonitoringFace that the community extends. Whereas the
[Infrastructure](../Infrastructure/README.md) provides the platform core (the abstract
base classes and services), the Archive holds the concrete, contributed artifacts that
plug into it. It is organized into three top-level directories:

| Directory | Contents |
|-----------|----------|
| **[`Docker/`](Docker)** | Dockerfiles (plus `tool.properties`) that package each tool, generator, oracle, converter, and case study, grouped by category. |
| **[`Implementations/`](Implementations)** | The Python wrapper classes that bind each packaged artifact to an Infrastructure base class. |
| **[`Experiments/`](Experiments)** | YAML experiment and suite configuration files, including the configs reproducing the paper's use cases and example case-study data. |

Existing entries are the best reference when adding a new one.

---

## `Docker/` — packaging components

`Docker/` is grouped by component category. Every category folder contains one
subfolder per component:

```
Docker/
├── Tools/             # Monitors and enforcers (DejaVu, EnfGuard, MonPoly, TeSSLa,
│                      #   TimelyMon, VeriMon, WhyMon, WhyMyMon)
├── DataGenerators/    # Trace generators (SignatureGenerator, PatternDataGenerator, …)
├── PolicyGenerators/  # Policy/formula generators (GenFmaGenerator, MfotlPolicyGenerator, …)
├── DataConverters/    # Trace-format converters (ReplayerConverter, …)
├── PolicyConverters/  # Policy-format converters (QTLConverter, …)
├── CaseStudies/       # Fixed real-world workloads (Nokia, GDPR, …)
└── Utilities/         # Supporting tools used by the categories above
```

Each component folder contains:

- a **`tool.properties`** metadata file, and
- one or both of **`offline/Dockerfile`** and **`online/Dockerfile`**, depending on
  which monitoring modes the tool supports.

The `tool.properties` metadata is used to query the git provider's API and resolve
version information (e.g. commit hashes) for reproducible builds.

### Dockerfile conventions

A component's Dockerfile provides the correct installation pipeline (special
dependencies, compiler flags, build steps) and must be compatible with the platform's
automation:

1. Use an appropriate base image for the tool's tech stack.
2. Install all build tools required (e.g. `git`, `cargo`, `gcc`, `opam`).
3. Clone the repository using an `ARG GIT_BRANCH` (and, where supported,
   `ARG GIT_COMMIT`) so the platform can build different branches/releases for version
   comparison. Build from authentic sources, or fetch authentic precompiled binaries.
4. Support **multi-architecture** builds (`amd64` and `arm64`).
5. In the final image, install **GNU time** so the platform can measure performance
   (`/usr/bin/time`).
6. Set the **entrypoint** to the tool's binary name in lower case.
7. Prefer **multi-stage builds** to minimize the final image size.

For *compiled* monitors (e.g. DejaVu), provide a build script (policy → binary) and a
run script (binary on a trace), exposed as container entrypoints. For *interpreted*
monitors (e.g. MonPoly), a single run script suffices.

### `tool.properties` fields

```properties
name=MonPoly        # original tool name, with original casing
git=BitBucket       # the git provider hosting the repo (GitHub, GitLab, BitBucket, …)
owner=jshs          # user/organization owning the repo
repo=monpoly        # repository name
```

Generators may additionally specify a `branch=` field naming the desired branch/state
of the repository. The existing entries cover all three git providers and can be
consulted for reference.

### Shared images (symbolic links)

When several tools share a single repository, Dockerfile, and binary, the dependent
folder contains a **`symbolic_link`** file holding the path (relative to `Docker/`) of
the folder to reuse, instead of duplicating the Dockerfile and `tool.properties`. For
example, `VeriMon` shares MonPoly's build — `Docker/Tools/VeriMon/offline/symbolic_link`
contains `/Tools/MonPoly` — and `Docker/DataGenerators/SignatureGenerator/symbolic_link`
points to `/DataGenerators/gen_data`.

### Case studies

A case study is a loose, two-part structure: a `data` folder containing all needed
files in any desired format, and an `instructions.txt` file in which each line
describes a combination of data, policy, and signature by giving the relative path
(from the case-study folder) to each element.

### Converters and utilities

Converters and utilities do not interact directly with the platform automation, so no
strict conventions are imposed — each is assumed to be tool-specific. They are still
encouraged to be as general as possible and to follow reasonable coding standards for
reuse.

---

## `Implementations/` — wrapper classes

`Implementations/` mirrors the component categories and holds the Python wrapper
classes that connect each packaged artifact to its Infrastructure base class:

```
Implementations/
├── Monitors/      # one folder per monitor; e.g. Monitors/MonPoly/MonPoly.py
├── Oracles/       # DataGolfOracle, VeriMonOracle
└── Builders/ProcessorBuilder/
    ├── DataGenerators/  PolicyGenerators/
    ├── DataConverters/  PolicyConverters/
    └── Utilities/
```

For **automatic discovery**, a component's folder name, file name, and class name must
match (case-sensitive) — e.g. `Monitors/TimelyMon/TimelyMon.py` defining
`class TimelyMon(...)`.

The wrapper conventions for each component type are documented with the base classes
in the Infrastructure:

- **Monitors** → extend `BaseMonitorTemplate`; see [Infrastructure/Monitors/README.md](../Infrastructure/Monitors/README.md).
- **Data / Policy generators** → extend `DataGeneratorTemplate` / `PolicyGeneratorTemplate`; see [Infrastructure/Builders/ProcessorBuilder/README.md](../Infrastructure/Builders/ProcessorBuilder/README.md).
- **Oracles**, **converters**, **case studies**, and **contracts** → see [Infrastructure/README.md](../Infrastructure/README.md) for the relevant base classes.

---

## `Experiments/` — configurations

`Experiments/` holds the YAML files that drive the platform. Configuration names passed
to the CLI are resolved relative to this directory. Notable subfolders:

- **[`examples/`](Experiments/examples)** — minimal example experiments and an example suite.
- **[`benchmark_paper/`](Experiments/benchmark_paper)** — the exact configurations used for the paper's use cases (correctness testing, regression testing, tool comparison, parameter tuning, online benchmarks).

See the [top-level README](../README.md#example-a-synthetic-experiment) for the YAML
schema and the [CLI Usage Guide](../Infrastructure/Frontend/CLI/CLI_USAGE.md) for the
full reference.
