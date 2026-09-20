#!/usr/bin/env python3
"""Pre-run formula search for the thesis clean-up tuning experiment.

Samples random formulas from the pinned MfotlPolicyGenerator (gen_for.py) with
boosted temporal-operator probabilities, then screens each candidate seed
against the defendability criteria:

  1. syntactic  -- contains at least one past temporal (ONCE/SINCE) AND one
                   future temporal (EVENTUALLY/UNTIL) operator with bounded
                   intervals, so both the past and the future clean-up
                   mechanisms of TimelyMon are exercised (merged operators are
                   ignored / not enabled);
  2. monitorable -- TimelyMon's own --check accepts the formula;
  3. behavioral -- on a signature-conform probe trace the run finishes within
                   the cap, builds real state, and is theta-SENSITIVE: eager
                   (0.0/0.0) vs lazy (0.9/0.9) static clean-up differ in peak
                   RSS or runtime by at least the sensitivity margin.

Winning seeds go verbatim into the experiment YAML's seeds block (the contract
constants below must match the YAML's policy_setup for seed transfer).
Phase 3 additionally reports, per winner, whether regenerating with a larger
-ub keeps the formula structure (deciding how the interval-scaling axis is
implemented: by ub, or by textual interval scaling of the fixed formula).

The probe trace approximates the SignatureGenerator (uniform values); the
final experiment uses the real generator through MonitoringFace.

Usage example (paths from the current scratch setup):
  python3 formula_search.py --gen <worktree>/gen_for.py \
      --gen-python <venv>/bin/python3 --tm <timelymon-binary> \
      --workdir <scratch>/search --seeds 200 --tps 20000 --cap 120
"""

import argparse
import csv
import random
import re
import subprocess
import sys
import time
from pathlib import Path

# Contract constants: MUST match policy_setup in tuning_temporal_clean_up.yaml
CONTRACT = [
    "-pred", "4", "-A", "2", "-S", "5",
    "-lb", "0", "-ub", "100", "-delta", "30",
    "-prob_once", "0.25", "-prob_since", "0.15",
    "-prob_eventually", "0.25", "-prob_until", "0.15",
    "-prob_eand", "0.1",
]
SCALED_UB = "1000"  # phase 3: structure stability under larger intervals

PAST_RE = re.compile(r"\b(ONCE|SINCE)\b")
FUTURE_RE = re.compile(r"\b(EVENTUALLY|UNTIL)\b")
UNBOUNDED_RE = re.compile(r"\[\s*\d+\s*,\s*(\*|INFINITY|inf)")
INTERVAL_RE = re.compile(r"\[\s*\d+\s*,\s*\d+\s*\]")


def run_gen(gen_python, gen_script, seed, ub=None):
    args = list(CONTRACT)
    if ub is not None:
        args[args.index("-ub") + 1] = ub
    out = subprocess.run(
        [gen_python, str(gen_script), *args, "-seed", str(seed)],
        capture_output=True, text=True, timeout=60,
        cwd=Path(gen_script).parent)
    if out.returncode != 0:
        return None, None
    try:
        _, rest = out.stdout.split("Seed:")
        _, rest = rest.split("Signature:")
        sig, formula = rest.split("MFOTL Formula:")
        return formula.strip(), sig.strip()
    except ValueError:
        return None, None


def parse_sig(sig_text):
    """-> [(name, arity)]"""
    preds = []
    for line in sig_text.splitlines():
        line = line.strip()
        m = re.match(r"(\w+)\(([^)]*)\)", line)
        if m:
            args = [a for a in m.group(2).split(",") if a.strip()]
            preds.append((m.group(1), len(args)))
    return preds


def write_probe_trace(path, preds, tps, rate, domain, seed):
    rng = random.Random(seed)
    with open(path, "w") as f:
        for tp in range(tps):
            for _ in range(rate):
                name, arity = rng.choice(preds)
                vals = "".join(f", x{i}={rng.randrange(domain)}" for i in range(arity))
                f.write(f"{name}, tp={tp}, ts={tp}{vals}\n")


def write_sig_file(path, preds):
    with open(path, "w") as f:
        for name, arity in preds:
            f.write(f"{name}({','.join(['int'] * arity)})\n")


def tm_check(tm, formula, sig_file):
    r = subprocess.run([tm, formula, "-c", "-s", str(sig_file)],
                       capture_output=True, text=True, timeout=60)
    return r.returncode == 0


def tm_run(tm, formula, sig_file, trace, theta, cap):
    cmd = ["/usr/bin/time", "-l", tm, formula, str(trace), "-s", str(sig_file),
           "-m", "3", "-w", "1",
           "--past-temporal-clean-up", str(theta),
           "--future-temporal-clean-up", str(theta),
           "--clean-up-step", "0.0"]
    t0 = time.monotonic()
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=cap)
    except subprocess.TimeoutExpired:
        return None, None, "timeout"
    wall = time.monotonic() - t0
    if r.returncode != 0:
        return None, None, f"exit {r.returncode}"
    m = re.search(r"(\d+)\s+maximum resident set size", r.stderr)
    rss = int(m.group(1)) if m else None
    return wall, rss, "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gen", required=True, help="path to gen_for.py (pinned worktree)")
    ap.add_argument("--gen-python", default=sys.executable)
    ap.add_argument("--tm", required=True, help="TimelyMon release binary (pinned commit)")
    ap.add_argument("--workdir", required=True)
    ap.add_argument("--seeds", type=int, default=200, help="candidate seeds 1..N")
    ap.add_argument("--tps", type=int, default=20000)
    ap.add_argument("--rate", type=int, default=10)
    ap.add_argument("--domain", type=int, default=1000)
    ap.add_argument("--cap", type=int, default=120, help="per-run timeout, seconds")
    ap.add_argument("--sensitivity", type=float, default=0.10,
                    help="relative theta-difference (RSS or time) to count as sensitive")
    ap.add_argument("--max-behavioral", type=int, default=40,
                    help="at most this many syntactic survivors go to phase 2")
    args = ap.parse_args()

    wd = Path(args.workdir)
    wd.mkdir(parents=True, exist_ok=True)
    rows = []
    survivors = []

    print(f"# phase 1: generate + syntactic screen, seeds 1..{args.seeds}", flush=True)
    for seed in range(1, args.seeds + 1):
        formula, sig = run_gen(args.gen_python, args.gen, seed)
        if formula is None:
            rows.append({"seed": seed, "status": "genfail"})
            continue
        has_past = bool(PAST_RE.search(formula))
        has_future = bool(FUTURE_RE.search(formula))
        unbounded = bool(UNBOUNDED_RE.search(formula))
        if not (has_past and has_future) or unbounded:
            rows.append({"seed": seed, "status": "syntax", "formula": formula})
            continue
        survivors.append((seed, formula, sig))
        rows.append({"seed": seed, "status": "candidate", "formula": formula})
    print(f"# {len(survivors)} syntactic survivors", flush=True)

    print("# phase 2: monitorability + behavioral screen", flush=True)
    results = []
    for seed, formula, sig in survivors[: args.max_behavioral]:
        preds = parse_sig(sig)
        sig_file = wd / f"s{seed}.sig"
        trace = wd / f"s{seed}.csv"
        write_sig_file(sig_file, preds)
        try:
            if not tm_check(args.tm, formula, sig_file):
                results.append({"seed": seed, "status": "unmonitorable", "formula": formula})
                print(f"seed {seed}: unmonitorable", flush=True)
                continue
        except subprocess.TimeoutExpired:
            results.append({"seed": seed, "status": "check-timeout", "formula": formula})
            continue
        write_probe_trace(trace, preds, args.tps, args.rate, args.domain, seed=314159265)
        t0, r0, s0 = tm_run(args.tm, formula, sig_file, trace, 0.0, args.cap)
        t9, r9, s9 = tm_run(args.tm, formula, sig_file, trace, 0.9, args.cap)
        trace.unlink()
        if s0 != "ok" or s9 != "ok":
            results.append({"seed": seed, "status": f"run({s0}/{s9})", "formula": formula})
            print(f"seed {seed}: {s0}/{s9}", flush=True)
            continue
        d_rss = abs(r9 - r0) / max(r0, 1)
        d_time = abs(t9 - t0) / max(t0, 1e-9)
        sensitive = d_rss >= args.sensitivity or d_time >= args.sensitivity
        results.append({
            "seed": seed, "status": "PASS" if sensitive else "insensitive",
            "formula": formula, "t_eager": round(t0, 2), "t_lazy": round(t9, 2),
            "rss_eager_mb": round(r0 / 2**20), "rss_lazy_mb": round(r9 / 2**20),
            "d_rss": round(d_rss, 3), "d_time": round(d_time, 3),
        })
        print(f"seed {seed}: {'PASS' if sensitive else 'insensitive'} "
              f"t {t0:.1f}/{t9:.1f}s rss {r0 >> 20}/{r9 >> 20}MB", flush=True)

    print("# phase 3: interval-scaling structure stability for passers", flush=True)
    for res in results:
        if res["status"] != "PASS":
            continue
        wide, _ = run_gen(args.gen_python, args.gen, res["seed"], ub=SCALED_UB)
        if wide is None:
            res["ub_scaling"] = "genfail"
        else:
            strip = lambda x: INTERVAL_RE.sub("[I]", x)
            res["ub_scaling"] = "stable" if strip(wide) == strip(res["formula"]) else "restructured"
        print(f"seed {res['seed']}: ub-scaling {res['ub_scaling']}", flush=True)

    out_csv = wd / "search_results.csv"
    fieldnames = ["seed", "status", "t_eager", "t_lazy", "rss_eager_mb",
                  "rss_lazy_mb", "d_rss", "d_time", "ub_scaling", "formula"]
    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in results:
            w.writerow(r)
    passed = [r for r in results if r["status"] == "PASS"]
    print(f"# done: {len(passed)} PASS of {len(results)} behaviorally screened; "
          f"results in {out_csv}", flush=True)


if __name__ == "__main__":
    main()
