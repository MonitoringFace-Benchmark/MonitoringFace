# EnfGuard benchmark suite as replayed in the EnfFlash evaluation (Table 1):
# the `nokia` benchmark with MonPoly's formulae and signature.
FROM alpine:latest

RUN apk add --no-cache git xz

ENV SUITE=/tmp/enfflash/eval/enforcement/benchmarks BENCH=nokia TOOL=monpoly FORMAT=mfotl

ARG GIT_BRANCH=main
ARG GIT_COMMIT=""
RUN git clone --filter=blob:none --no-checkout --branch "$GIT_BRANCH" https://github.com/runtime-enforcement/EnfFlash.git /tmp/enfflash \
    && cd /tmp/enfflash \
    && git sparse-checkout set --no-cone "/eval/enforcement/benchmarks/$BENCH/" /eval/enforcement/benchmarks/large/ \
    && git checkout "${GIT_COMMIT:-HEAD}"

# committed xz-compressed and split (eval/paper/large_logs.sh); checksum as in
# eval/paper/docker/data.sha256
RUN ls "$SUITE"/large/$BENCH.log.xz.part-* >/dev/null 2>&1 || { \
        echo "eval/enforcement/benchmarks/large/$BENCH.log.xz.part-* missing at this EnfFlash commit" >&2; exit 1; } \
    && cat "$SUITE"/large/$BENCH.log.xz.part-* | xz -d > /tmp/benchmark.log \
    && echo "ff2ba80618eecc560b83f509bbc30c0d356083513e2ecf8969f8f60232277c60  /tmp/benchmark.log" | sha256sum -c -

# Lines are `<replay time>|<MonPoly time-point>`: keep the time-point, one per line
RUN mkdir -p /suite/data/Formula /suite/data/Signature /suite/data/Trace \
    && cp -L "$SUITE/$BENCH/$TOOL"/formulae/* /suite/data/Formula/ \
    && cp -L "$SUITE/$BENCH/$TOOL/signature.sig" /suite/data/Signature/signature.sig \
    && cut -d'|' -f2- /tmp/benchmark.log > /suite/data/Trace/trace.log \
    && rm /tmp/benchmark.log \
    && { echo "Trace, Policy, Signature"; \
          for f in $(ls /suite/data/Formula); do \
              echo "Trace/trace.log: monpoly, Formula/$f: $FORMAT, Signature/signature.sig"; \
          done; } > /suite/instructions.txt

WORKDIR /data

# the container runs as root: leave the unpacked files writable for the host user
CMD sh -c "cp -r /suite/data . && cp /suite/instructions.txt . && chmod -R a+rwX data instructions.txt"
