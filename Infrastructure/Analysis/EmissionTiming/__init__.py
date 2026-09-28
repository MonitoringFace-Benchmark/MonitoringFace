"""When each verdict was emitted, across tools and runs, in log time.

extract turns an online run's frames into one emission per verdict; compare
joins emissions of several tools (possibly from different runs over the
same data) into a correctness gate against a reference tool and the lead of
every tool over a baseline tool. Run from the project root:

    python -m Infrastructure.Analysis.EmissionTiming <run_dir> [<run_dir> ...] \\
        --reference VeriMon --baseline MonPoly
"""
