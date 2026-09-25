# Thesis development-support experiments (Chapter 6)

Two experiments that showcase MonitoringFace's development-support use cases through
TimelyMon: parameter tuning (`tuning_temporal_clean_up.yaml`) and regression testing over
real development history (`regression_perf_audit.yaml`). Both run the identical synthetic
policy/data matrix (same cells, same seeds), so results are comparable across the two.

## Shared matrix

| Axis | Values |
|---|---|
| Formulas | Fixed winners of the pre-run formula search (below). Experiment 1 and the interval-scaling companion: settings 0–9; experiment 2: settings 0–3 (the same first four) |
| Trace sizes | Experiment 1: 10 000–100 000 time points in five steps; interval companion: 10 000 / 100 000; experiment 2: 10 000 / 50 000 / 100 000. Event rate 10, so events = 10 × time points (100 K – 1 M) |
| Seeds | `[gen_seed, policy_seed]` per setting; the policy seed is the search-winner seed, the shared data seed (314159265) makes traces differ only by size |
| Per-run cap | 300 s (`runtime_constraints.upper_bound`); raise for the final thesis run if lazy lanes time out |
| Measured | wall-clock runtime, peak memory, output counts (`outputs` / `distinct_outputs`) |

## Pre-run formula search (`formula_search.py`, results in `formula_search_results.csv`)

Random formulas cannot be assumed to exercise the clean-up mechanism — probing showed even
multi-GB-state formulas can be completely θ-insensitive. The search samples the pinned
`MfotlPolicyGenerator` (`fef5f8f5`, 300 seeds) at the exact contract the experiments declare
(4 predicates, 5 operators, 2 free vars, bounded intervals `lb 0 / ub 100 / delta 30`,
P(once)=.25, P(since)=.15, P(eventually)=.25, P(until)=.15, P(eand)=.1) and keeps a seed only
if: it contains bounded past (ONCE/SINCE) **and** future (EVENTUALLY/UNTIL) operators — the
consumers of the two temporal thresholds (merged operators unused); TimelyMon `--check`
accepts it; and on a 200 K-event probe it finishes in budget and is **θ-sensitive** (≥10 %
relative eager-vs-lazy difference in peak RSS or runtime). 17 of 40 behaviorally screened
seeds passed; the 10 fixed winners (all structure-stable under `ub`×10, seed 139 dropped for
runtime, 125 for weak sensitivity):

| Setting | Seed | θ-effect on probe (eager→lazy) |
|---|---|---|
| 0 | 12 | RSS 177→144 MB, time +14 % |
| 1 | 22 | RSS 97→113 MB |
| 2 | 45 | RSS 158→136 MB |
| 3 | 135 | time +13 % |
| 4 | 146 | RSS 125→155 MB |
| 5 | 161 | RSS 105→118 MB |
| 6 | 168 | time +13 % |
| 7 | 174 | time +13 % |
| 8 | 182 | RSS 118→150 MB |
| 9 | 185 | time +29 % |

Note the direction varies: lazy sometimes peaks *lower* than eager (GC churn vs retention) —
part of what the full sweep maps out. The `policy_setup` blocks must stay flag-identical to
the search contract (omitted fields stay omitted), or the seeds regenerate different
formulas.

## Interval-size axis (`tuning_interval_scaling.yaml`)

Same 10 lanes and winner seeds as experiment 1 with the contract's `ub` scaled ×10 (1000);
search phase 3 verified all 10 winners regenerate structurally identical formulas, so cells
differ in window width alone. Two sizes (10 K / 100 K tps), 200 runs.

## Experiment 1 — parameter tuning (`tuning_temporal_clean_up.yaml`)

Fixed commit `perf-audit-2026-09 @ ad330931` (newest committed state with the
fraction-outdated clean-up semantics and the adaptive step). 10 lanes:
θ ∈ {0.0, 0.1, 0.3, 0.6, 0.9} on **both** temporal thresholds
(`--past-temporal-clean-up`, `--future-temporal-clean-up`) × `--clean-up-step`
∈ {0.0 static, 0.025 adaptive}. Relational threshold pinned at the default 0.1 in every
lane: the audit found it inert (frontier, not threshold, gates join GC), and fixing it keeps
the sweep attributable to the temporal thresholds. Workers fixed at 1 to isolate GC from the
multi-worker feeding effect (F2). 10 lanes × 10 settings × 5 sizes = 500 runs.

**Reachability caveat**: like the regression experiment's missing sixth lane, all tuning
lanes pin `ad330931` on `perf-audit-2026-09`, which is not on `git.ku.dk` yet — the branch
must be pushed before MonitoringFace can build either tuning experiment.

Questions the table answers: where the CPU-vs-memory sweet spot lies per formula/size;
whether the adaptive step converges to the best static threshold from both the eager and the
lazy start; and (via identical `distinct_outputs` across lanes) that clean-up is
semantics-neutral.

## Experiment 2 — regression testing (`regression_perf_audit.yaml`)

Five pinned commits × workers {1, 4}, default thresholds, 10 × 4 × 3 = 120 runs.
Exact changes per lane:

| Lane | Commit (branch) | Exact change vs previous lane |
|---|---|---|
| 1 | `ec86e20a` (development) | Baseline; pre-audit state, same pin as `ooo_claim_family.yaml` |
| 2 | `dc88da9a` (development) | Shadow-agenda validation harness removed (compile-time feature; expected runtime-neutral — null check) |
| 3 | `b0248ab4` (development) | Watermark forced emission steps to quiescence instead of once |
| 4 | `e5e64e1d` (development) | `c4a82d1d`: True/Value streams get range emitters via shared `range_leaf`, empty-payload bug fixed; `e5e64e1d` itself adds `.gitignore` only. This commit is the perf audit's baseline binary |
| 5 | `f6e7e6d1` (development, head) | Online path: watermark releases drained on their own line, idle-tolerant. Online-only; offline numbers expected equal to lane 4 (null check) |

A sixth lane with the audit follow-ups (`4baad676` on `perf-audit-2026-09`: streaming
executor / per-time-point sessions (F6), ingestion barrier (F2), ObservationSequence cached
views (F5), `--ts-lookahead` pre-feeding) is currently unreachable — that branch is not on
`git.ku.dk`; re-add it once pushed.

Expected effects (from `PERF_AUDIT_2026-09-15.md`, measured by hand on Apple M2 Pro): every
lane at 4 workers shows the F2 frontier-stall pathology (Linear: 2.3 GB RSS vs 273 MB at
1 worker) — its fix lives in the unreachable follow-ups commit. Lanes 2 and 5 are deliberate
null checks. `distinct_outputs` must agree across all lanes in every cell; any deviation is
a caught regression.

## Experiment 2b — framework-version regression (`regression_framework_versions.yaml`)

Same matrix and workers as experiment 2 (settings 0–3, sizes 10 K / 50 K / 100 K tps,
workers {1, 4}), but the lanes isolate the **timely dataflow dependency**: three branches
share the TimelyMon source at `a71920e9` (= lane 5's `f6e7e6d1` + `e0b6e36c` float parsing +
`a71920e9` ungrouped-aggregation fix) and differ only in `Cargo.toml`/`Cargo.lock`.
3 lanes × 2 workers × 4 settings × 3 sizes = 72 runs.

| Lane | Branch (commit) | timely |
|---|---|---|
| 1 | `framework_version_29` @ `a71920e9` | 0.29.0 (baseline) |
| 2 | `framework_version_30` @ `d639b6e7` | 0.30.0 |
| 3 | `framework_version_31` @ `d635bcda` | 0.31.0 |

All three branches are pushed on `git.ku.dk`, so — unlike the tuning experiment's
`perf-audit-2026-09` pin and experiment 2's missing sixth lane — every lane is reachable.

Correctness is checked two ways. `distinct_outputs` must be identical across the three
lanes in every cell; any deviation is a semantic regression introduced by the framework
upgrade. In addition — unlike experiment 2, which runs oracle-free — the **VeriMon oracle**
(pin `bc752d37`, as in use cases 5.1/5.3; VeriMon also runs as a lane, as the oracle
machinery expects) gives ground truth per cell; VeriMon may exceed the 300 s cap on the
largest size, where the cross-lane equality check still covers the cell. Runtime and peak
RSS quantify the upgrade's performance effect. Caveat carried over from the TimelyMon-side measurements
(2026-09-24/25, timelymon `verify_reports/harness/`): separate release builds with default
codegen units plus per-process variance move single cells by up to ~10–20 %, so only
effects beyond that, or consistent across settings and sizes, count as a regression.

## Notes and caveats

- Peak memory is recorded per run; there is no continuous memory profile.
- The pins reference committed states only. The timelymon working tree currently carries
  uncommitted modifications (`main.rs`, `fast_hash.rs`, `temporal_state_cleaner.rs`, the
  until/since partial sequences); those are not covered by any lane until committed.
- The adapter (`Archive/Implementations/Monitors/TimelyMon`) already forwards `worker`,
  `output_mode`, and all four clean-up parameters; `--ts-lookahead`,
  `--inflight-watermarks`, and `--merged-connectives` are not yet forwarded (each a small
  adapter addition if a follow-up experiment wants to sweep them).
- Output mode 1 (stdout printing) is used in every lane so output counts are comparable;
  the printing cost is identical across lanes of an experiment and therefore cancels in
  comparisons.
- Old commits predate the clean-up flags; experiment 2 deliberately passes only
  `worker`/`output_mode`, which every pinned commit accepts.
