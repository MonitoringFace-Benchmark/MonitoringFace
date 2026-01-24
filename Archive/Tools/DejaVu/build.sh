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


if [ "$#" -lt 1 ]; then
    echo "Usage: build <specFile>"
    exit 1
fi
SPEC=$1
DEJAVU=/home/dejavu

SPECHASH=$(cat $SPEC | md5sum | cut -d' ' -f1)
SPECFOLDER=$(echo $SPEC-$SPECHASH)

echo $SPECFOLDER

if [ ! -e ${SPECFOLDER}/TraceMonitor.class ]; then
    mkdir -p ${SPECFOLDER}
    # Parse specification and synthesize monitor:
    java -cp $DEJAVU/dejavu.jar dejavu.Verify $SPEC > /dev/null 2>&1
    # Compile synthesized monitor:
    scalac -cp .:$DEJAVU/dejavu.jar TraceMonitor.scala > /dev/null 2>&1

    res=$?
    if [ $res -ne 0 ]; then
        echo "DejaVu: Error during specification parsing or monitor synthesis."
        exit $res
    fi

    mv *.class ${SPECFOLDER}
    mv TraceMonitor.scala ${SPECFOLDER}
    mv ast.dot ${SPECFOLDER}
fi