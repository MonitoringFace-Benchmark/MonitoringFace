# Plan: limits of early reporting (A) and settling before the watermark (B)

Status 2026-10-02: P0.1 and P0.3 done, regression run green (see "Phase 0
results" at the end); P0.4 to P0.7 and the experiments not started. Builds on
the late-replication hook (`thesis_ahead_motivation_*`) and the claim-family
online experiments (`ooo_claim_family{,_future}_online.yaml`, runs of
2026-09-18).

## The story

1. **Hook (done).** Late replication on the in-order Nokia log. A witness (the
   copy) decides each verdict. TimelyMon reports at the witness, MonPoly once the
   window has closed: median lead 59 s, mean 64.2 s, max 2,501 s, never later.
2. **Experiment A (limits).** Random formulas mixing past and future operators on
   medium-delayed data. How close does each monitor get to the earliest emission
   any sound monitor can achieve, and what does in-order processing cost?
3. **Experiment B (settling before the watermark).** Negated future operators,
   whose verdicts are absences and need a closed window. A late straggler holds
   the prefix watermark back. Does tp-interval-timestamp settle these verdicts
   from point claims before the watermark, and does that vanish when claims
   arrive as a prefix (control)?

## Shared setup

### Lanes (as in `ooo_claim_family_future_online.yaml`)

| lane | input | progress information | role |
|---|---|---|---|
| MonPoly | Disorderer (bridge) then dynamic Sorter | sorted blocks | in-order baseline |
| TimelyMon common (development) | Disorderer (csv) then dynamic PrefixRebuilder | `>WATERMARK n<`, a prefix (exclusive) | watermark monitor |
| TimelyMon tp-interval (tp-interval-timestamp) | Disorderer (csv), identity | `>ELAPSED tp @ ts<`, single points with their timestamp | settled-set monitor |
| OOOMon (main) | Disorderer (csv), identity | ELAPSED points | the limit |

All lanes read the same disordered stream (shared Disorderer params through a
YAML anchor; `format` is exempt), so the input position, lines fed (data and
claims), is a coordinate common to all lanes.

### The limit

`monitor_correct_r` (Progress/EndToEndRefined.thy): after any input prefix the
output so far is exactly `rverdicts (RSS π) π φ`, the verdicts settled by that
prefix. OOOMon therefore emits every verdict at the first input position where
it is settled, which serves as the reference for the earliest possible
emission. To confirm in P0.7: whether RSS is proven maximal (no sound monitor
decides more from the same prefix). If it is, OOOMon's curve is the limit; if
not, call it the limit under refined settledness.

### Measurement

- **Coordinate:** lines fed, from the driver frames (rounds as a secondary axis).
- **Per verdict and lane:** the first emission position.
- **Lead decomposition per verdict, in lines:**
  - price of in-orderness = MonPoly − common;
  - price of prefix closure = common − tp-interval;
  - distance to the limit = tp-interval − OOOMon (expected 0).
- **Curves:** cumulative verdicts against lines fed, one panel per setting, with
  OOOMon dashed, as on the claim-family page.
- **Correctness gate:** identical verdict multisets in all four lanes (count
  pairs, not distinct, so duplicate emissions show), plus VeriMon offline on the
  in-order trace as an independent reference. A failing setting is
  investigated, never dropped.
- **Accounting:** TimelyMon and OOOMon run in lockstep (event-count, one line per
  round); their attribution is exact (dominance audit of 2026-09-18). MonPoly
  runs behind a dynamic Sorter under chain accounting, which can only attribute
  late and would overstate leads; P0.3 makes it exact.

## Experiment A: limits with past and future operators

- **Formulas:** random, 10 operators, 2 free variables, 4 predicates, bounded past
  and future operators both present (for example `prob_once`, `prob_since`,
  `prob_eventually`, `prob_until` at 0.2 each; `ub` 10, `delta` 10). Selected
  by a formula search in the style of `formula_search.py`:
  1. syntactic: at least one past and one future bounded operator;
  2. monitorable by all four (TimelyMon `--check`, OOOFragmentConverter plus
     `wf_tra`, MonPoly);
  3. non-vacuous: at least 20 verdicts on the probe trace;
  4. OOOMon finishes within 60 s on the probe trace.

  Six formulas.
- **Data:** SignatureGenerator, 100 time points of 10 events (1,000 events), with
  `domain` 30 so cross-time-point joins match, and two data seeds.
- **Disorder ("medium"):** Disorderer with geometric delays, `fraction_displaced`
  1.0, `granularity` event, `claim_order` independent, `lag` 8.
  `displacement_bound` is calibrated in P0.5 so that the prefix watermark trails
  the newest data by about half the formulas' median window; the starting point
  is 50 lines, about 5 time points.
- **Settings:** 6 formulas × 2 data seeds = 12.
- **Expected:**
  - tp-interval equal to OOOMon pointwise, as in both claim families;
  - common at the limit on positive future parts, which the window gates;
  - a small prefix-closure price on past parts;
  - MonPoly behind everywhere, by the sorting delay plus the window.
- **Outputs:**
  - per-setting curves with the limit;
  - a table per setting: verdicts, agreement, each lane's median and max lead
    over MonPoly, the share of each lane's verdicts emitted at the limit, and
    the decomposition.

## Experiment B: negated future operators settled before the watermark

- **Formulas:** Nand-headed shapes whose negated side holds a bounded future
  operator: `α AND NOT EVENTUALLY[a,b] β` and `α AND NOT (β UNTIL[a,b] γ)`, with
  composite operands allowed. The generator produces negation only as Nand.
  Random formulas (high `prob_nand`, high `prob_eventually`/`prob_until`,
  `prob_once`/`prob_since` 0), screened for:
  - the negated side contains EVENTUALLY or UNTIL;
  - non-vacuous;
  - monitorable by all four.

  Plus two hand-written templates for the text, one NOT EVENTUALLY and one NOT
  UNTIL. Six formulas in all.
- **Disorder (stragglers):** most events in order, a few very late:
  `fraction_displaced` 0.05, `delay_distribution` heavytail,
  `displacement_bound` 200 lines (about 20 time points), `lag` 8. A straggler
  at time point s holds the prefix watermark at s, while windows entirely
  above s are complete and claimed.
- **Control:** the same with `claim_order` downward-closed. Claims then arrive
  only as a prefix, settled sets are prefixes, and tp-interval should equal the
  common lane.
- **Settings:** 6 formulas × 2 data seeds × {independent, downward-closed} = 24.
- **Measures:**
  - the verdicts settled before the watermark (tp-interval earlier than common),
    with their lead in lines and in claims;
  - each lane's lead over MonPoly;
  - tp-interval against OOOMon (expected equal);
  - a mechanism check: for every early verdict, the straggler that held the
    watermark lies below the verdict's window.
- **Expected:**
  - with independent claims, a clear share of the negated-future verdicts is
    emitted before the watermark, with a lead about the straggler's delay;
  - in the control, none.

## Phase 0: prerequisites

- **P0.1 Builds and pins.**
  - development is local `4a0ba6c9`, 3 commits ahead of origin (the PartialSequence
    `merge_left` fix).
  - tp-interval-timestamp is local `4e51173a`, 1 ahead (the same fix), and lacks
    98 development commits: the clean-up rework, and the projection and
    merged-join fixes.
  - Recommendation: push both and pin them. Don't merge development into
    tp-interval-timestamp for these experiments. The missing fixes concern
    memory on long runs and `--merged-connectives`, neither of which matters at
    1,000 events without the flag.
- **P0.2 OOOMon pin.** The claim configs pin `6218df6`; main is at `17b943a`
  (2026-09-30). Keep `6218df6` unless the claim-family four-way agreement is
  green on `17b943a`.
- **P0.3 Exact MonPoly attribution behind the Sorter.**
  - Recommended: replay the Sorter's released blocks offline through the pinned
    MonPoly in `process-step` lockstep, map each released block to the fed
    position that released it (the Sorter's origins in the frames), and take
    MonPoly's emission position from there.
  - Alternative: make the driver accept `process-step` together with
    processors.
  - Also check that the MonPoly invocation carries `-nofilteremptytp
    -nofilterrel`; without them it reports false violations on future formulas.
- **P0.4 Analysis.** Extend EmissionTiming with the lines-fed coordinate,
  OOOMon as the reference, MonPoly as the baseline, the lead decomposition, and
  cumulative curves (`plot.py`) with the limit lane.
- **P0.5 Calibration.** "Medium" disorder for A and the straggler parameters for
  B, from the Disorderer's stats (`peak_open_timepoints`, watermark lag) on the
  chosen traces.
- **P0.6 Formula search** for A and B, extending `formula_search.py` with the
  criteria above.
- **P0.7 The theorem to cite** for the limit: `monitor_correct_r`, plus maximality
  of RSS if proven.

## Order of work

1. P0.1 to P0.3, then a regression check: rerun `ooo_claim_family_future_online`
   with the new pins and confirm the 2026-09-18 four-way agreement and dominance
   still hold.
2. P0.4 to P0.6, then the Experiment A configs, runs and figures.
3. The Experiment B configs, including the control, then runs and figures.

## Open decisions (with recommendations)

- **Formula size:** 10 operators, as in the earlier three-ingredient design, if
  OOOMon stays within about 60 s per setting; otherwise 8. OOOMon took 0.5 to
  6 s on 5-operator formulas at 1,000 events, and scales about N^4 in the trace.
- **Medium disorder:** defined relative to the windows (watermark lag about half
  the median window) and calibrated, rather than as a fixed number of lines.
- **MonPoly attribution:** the offline replay (P0.3) rather than a driver
  change.

## Phase 0 results (2026-10-02)

- **P0.1.** Pushed development `4a0ba6c9` and tp-interval-timestamp `4e51173a`;
  `ooo_claim_family_future_online.yaml` pins both (uncommitted).
- **P0.3.** `Infrastructure/Analysis/EmissionTiming/sorted_lane.py` writes
  `frames/<setting>__MonPoly_exact.json`. It replays the stored fed stream
  through the Sorter, runs the pinned MonPoly once over the released blocks
  and credits step k to the fed line that released block k. It stops if the
  stored stream differs from the lane's recorded input or if block k is not
  tp k.
  - MonPoly ends a time point only at the next `@` or at a `;`. The Sorter's
    blocks carry no `;`, so on the lane MonPoly prints step k once block k+1
    has arrived. Crediting step k to block k is the position MonPoly reaches
    with `;`-terminated blocks, the earliest it can report (checked on the
    pinned binary).
  - `extract.py` now also reads OOOMon's native output (`@tp (v1,v2)`).
- **Regression run** `results/ooo_claim_family_future_online_20261002_201548`
  (four 5-operator future formulas, 1,000 events + 100 claims, uniform bound
  20):
  - All five frames (MonPoly chain, MonPoly exact, common, tp-interval,
    OOOMon) carry identical verdict multisets: 3,018 / 401 / 6,803 / 2,031,
    no duplicates, nothing unmapped.
  - OOOMon, tp-interval and common emit every verdict at the same line. On
    these positive future formulas there is no prefix-closure price, so B
    needs negated future operators, as planned.
  - TimelyMon is earlier than exact MonPoly on every verdict: in lines fed,
    median 36 to 226 (max 64 to 253); in log time, median 3 to 20 s (max 6 to
    23 s). Most of it is the window. The formulas nest futures with a reach of
    up to 23 time units, and MonPoly reports at window closure, TimelyMon at
    the witness.
  - Exact MonPoly is never later than the chain frame. The chain frame equals
    the exact attribution moved to block k+1's release (the lookahead, about
    11 lines) plus harvest slack of 0 to 3 rounds (13 verdicts: 6 or 19).
- **Not done:** P0.2 (OOOMon stays at `6218df6`), P0.4 (lines-fed coordinate
  in EmissionTiming; the check above is a scratch script), P0.5 to P0.7.
