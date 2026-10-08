# EnfGuard benchmark suite as replayed in the EnfFlash evaluation (Table 1):
# the `fun` benchmark with EnfGuard's formulae and signature; each formula
# comes with the functions it calls.
FROM alpine:latest

RUN apk add --no-cache git xz

ENV SUITE=/tmp/enfflash/eval/enforcement/benchmarks BENCH=fun TOOL=enfguard FORMAT=mfotl

ARG GIT_BRANCH=main
ARG GIT_COMMIT=""
RUN git clone --filter=blob:none --no-checkout --branch "$GIT_BRANCH" https://github.com/runtime-enforcement/EnfFlash.git /tmp/enfflash \
    && cd /tmp/enfflash \
    && git sparse-checkout set --no-cone "/eval/enforcement/benchmarks/$BENCH/" /eval/enforcement/benchmarks/large/ \
    && git checkout "${GIT_COMMIT:-HEAD}"

# the tool's copy of the benchmark log (all tools' copies are identical)
RUN cp -L "$SUITE/$BENCH/$TOOL/logs/log.log" /tmp/benchmark.log

# Lines are `<replay time>|<MonPoly time-point>`: keep the time-point, one per line
RUN mkdir -p /suite/data/Formula /suite/data/Signature /suite/data/Trace /suite/data/Functions \
    && cp -L "$SUITE/$BENCH/$TOOL"/formulae/* /suite/data/Formula/ \
    && cp -L "$SUITE/$BENCH/$TOOL/signature.sig" /suite/data/Signature/signature.sig \
    && cp -L "$SUITE/$BENCH/$TOOL/functions.py" /suite/data/Functions/functions.py \
    && cut -d'|' -f2- /tmp/benchmark.log > /suite/data/Trace/trace.log \
    && rm /tmp/benchmark.log \
    && { echo "Trace, Policy, Signature, Functions"; \
          for f in $(ls /suite/data/Formula); do \
              echo "Trace/trace.log: monpoly, Formula/$f: $FORMAT, Signature/signature.sig, Functions/functions.py"; \
          done; } > /suite/instructions.txt

WORKDIR /data

# the container runs as root: leave the unpacked files writable for the host user
CMD sh -c "cp -r /suite/data . && cp /suite/instructions.txt . && chmod -R a+rwX data instructions.txt"
