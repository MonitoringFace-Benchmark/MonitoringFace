#!/bin/bash

#
# DejaVu - a tool for checking past time temporal logic properties in QTL against traces in CSV format.
#
# To use, call (after making executable with: chmod +x dejavu) as follows:
#
#   dejavu <specFile> <traceFile> [<bitsPerVariable> [debug]]

# SCRIPT_PATH="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
# CALLING_DIR="$(pwd)"
# echo "DejaVu called from: $CALLING_DIR"
# echo "DejaVu script path: $SCRIPT_PATH"


if [ "$#" -lt 2 ]; then
    echo "Usage: run <specFile> <traceFile> [<outputDir>] [<bitsPerVariable> [debug]]"
    exit 1
fi
SPEC=$1
LOG=$2
OUTDIR=${3:-.}
BDDSIZE=${4:-20} # default number of bits per variable = 20
DEBUG=${5:-} # default is no debugging

DEJAVU=/home/dejavu

SPECHASH=$(cat $SPEC | md5sum | cut -d' ' -f1)
SPECFOLDER=${OUTDIR}/$(basename $SPEC)-$SPECHASH

dejavu_diagnose() {
    {
        echo "--- DejaVu run.sh diagnostics ---"
        echo "pwd:         $(pwd)"
        echo "OUTDIR:      ${OUTDIR}"
        echo "SPECFOLDER:  ${SPECFOLDER}"
        echo "outdir -d:   $(test -d "${OUTDIR}" && echo yes || echo NO)"
        echo "outdir -w:   $(test -w "${OUTDIR}" && echo yes || echo NO)"
        echo "ls -la .:";          ls -la . 2>&1 | sed 's/^/    /'
        echo "ls -la ${OUTDIR}:";  ls -la "${OUTDIR}" 2>&1 | sed 's/^/    /'
        echo "--- end diagnostics ---"
    } >&2
}

# Create it, and honour the caller's OUTDIR instead of a hardcoded path.
if ! mkdir -p "${OUTDIR}"; then
    echo "DejaVu: cannot create output directory ${OUTDIR}" >&2
    dejavu_diagnose
    exit 1
fi

# Keep the stats off OUTDIR entirely. OUTDIR is a bind mount, and
# /usr/bin/time opens its -o file before forking, so any hiccup creating that
# file aborts the run before the monitor starts. Nothing reads this file: the
# framework wraps this whole script in its own /usr/bin/time and copies its
# result over OUTDIR/stats.txt after we exit, so anything written here is
# overwritten. It is kept only so the script still reports timings when run
# standalone, outside the platform.
STATS_TMP="$(mktemp -t dejavu-stats.XXXXXX)"

# Run the compiled monitor on trace:
/usr/bin/time -v -o "${STATS_TMP}" scala -J-Xmx16g -cp .:$DEJAVU/dejavu.jar:${SPECFOLDER} TraceMonitor $LOG $BDDSIZE $DEBUG | egrep "\*\*\*"

res=${PIPESTATUS[0]}

rm -f "${STATS_TMP}"

if [ $res -ne 0 ]; then
    echo "DejaVu: Error during trace monitoring."
    # 125 is /usr/bin/time's "could not run the command": the monitor never
    # started, so the message above is about time, not about monitoring.
    if [ $res -eq 125 ]; then
        echo "DejaVu: exit 125 comes from /usr/bin/time, the monitor never ran" >&2
        dejavu_diagnose
    fi
    exit $res
fi
rm -rf dejavu-results