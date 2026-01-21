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
    echo "Usage: dejavu <specFile> <traceFile> [<bitsPerVariable> [debug]]"
    exit 1
fi
SPEC=$1
LOG=$2
BDDSIZE=${3:-20} # default number of bits per variable = 20
DEBUG=${4:-} # default is no debugging

DEJAVU=/home/dejavu

SPECHASH=$(cat $SPEC | md5sum | cut -d' ' -f1)
SPECFOLDER=$(echo $SPEC-$SPECHASH)

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


# Run the compiled monitor on trace:
scala -J-Xmx16g -cp .:$DEJAVU/dejavu.jar:${SPECFOLDER} TraceMonitor $LOG $BDDSIZE $DEBUG > ${SPECFOLDER}/dejavu_output.txt
res=$?
cat ${SPECFOLDER}/dejavu_output.txt | egrep "\*\*\*"

if [ $res -ne 0 ]; then
    echo "DejaVu: Error during trace monitoring."
    exit $res
fi
rm -rf dejavu-results
