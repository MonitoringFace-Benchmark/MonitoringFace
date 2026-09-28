import argparse
import csv
import os
import sys
from dataclasses import asdict

from Infrastructure.Analysis.EmissionTiming.compare import compare
from Infrastructure.Analysis.EmissionTiming.extract import extract_runs


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m Infrastructure.Analysis.EmissionTiming",
        description="Correctness gate and per-verdict lead in log time from online frames.")
    parser.add_argument("run_dirs", nargs="+", help="result folders of online runs (each with frames/)")
    parser.add_argument("--reference", required=True, help="tool whose verdicts define correctness")
    parser.add_argument("--baseline", required=True, help="tool the lead is measured against")
    parser.add_argument("--out", help="output folder (default: <first run_dir>/emission_timing)")
    args = parser.parse_args(argv)

    out = args.out or os.path.join(args.run_dirs[0], "emission_timing")
    failed = False
    for report in compare(extract_runs(args.run_dirs), args.reference, args.baseline):
        folder = os.path.join(out, report.setting)
        os.makedirs(folder, exist_ok=True)
        print(f"== setting {report.setting}: reference {report.reference}, baseline {report.baseline}")
        if not report.points_agree:
            print("   time-points DIFFER between the runs (not the same input)")
            failed = True
        summary = []
        for t in report.tools:
            gate = "ok" if not (t.extra or t.missing or t.duplicates or t.unmapped) else "FAILED"
            timed = t.tool not in (report.reference, report.baseline)
            failed |= gate != "ok" or (timed and t.later_than_baseline > 0)
            lead = t.lead
            print(f"   {t.tool:24s} verdicts {t.verdicts:6d}  gate {gate} (extra {t.extra}, missing {t.missing}, "
                  f"duplicates {t.duplicates}, unmapped {t.unmapped})"
                  f"{'  [valuations compared unordered]' if t.unordered_match else ''}")
            if timed:
                print(f"   {'':24s} lead over {report.baseline} (s): min {lead['min']}  median {lead['median']}  "
                      f"mean {lead['mean']}  p99 {lead['p99']}  max {lead['max']}  "
                      f"later {t.later_than_baseline}  end-of-input only {t.tail_only}")
            row = asdict(t)
            row.update({f"lead_{k}": v for k, v in row.pop("lead").items()})
            summary.append(row)
        for name, rows in (("summary.csv", summary), ("verdicts.csv", report.rows)):
            if rows:
                with open(os.path.join(folder, name), "w", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
                    writer.writeheader()
                    writer.writerows(rows)
        print(f"   written to {folder}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
