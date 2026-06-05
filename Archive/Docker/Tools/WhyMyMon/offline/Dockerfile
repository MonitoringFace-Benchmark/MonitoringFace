# syntax=docker/dockerfile:1
###############################################################################
# WhyMyMon + its three external "emonitors": MonPoly/VeriMon, DejaVu, TimelyMon
#
# WhyMyMon does not link the backend monitors; it spawns each as a child
# process (see src/monitor.ml:run_emonitor -> Emonitor.args). With
# "-path default" it looks each one up at a hard-coded location from
# src/argument.ml (Monitor.exec_path), RELATIVE to the process working dir:
#
#     MonPoly / VeriMon  ->  _build/install/default/bin/monpoly   (VeriMon = monpoly -verified)
#     DejaVu             ->  third-party/dejavu-online/out/dejavu-online
#     TimelyMon          ->  third-party/timelymon/target/release/timelymon
#
# So the runtime image fixes WORKDIR=/app and drops each binary at exactly
# that relative path. Run whymymon from /app and "-path default" resolves all
# three. (You can always override per run with "-path /abs/path/to/binary".)
#
# Build:  docker build -t whymymon .
# Run  :  docker run --rm -i whymymon whymymon -cli -monitor timelymon -path default \
#             -sig f.sig -formula f.mfotl -log /dev/stdin   < trace.log
###############################################################################

ARG WHYMYMON_BRANCH=main
ARG WHYMYMON_COMMIT=""
# MonPoly commit pinned by whymymon/third-party/download.sh
ARG MONPOLY_COMMIT=d0dc92d40ecab5fe088470125a0681a010e2a12b
ARG DEJAVU_REPO=https://github.com/leonardolima/dejavu-online.git
ARG TIMELYMON_REPO=https://git.ku.dk/kfx532/timelymon.git
ARG SCALA_VERSION=2.11.12

###############################################################################
# Stage 1 — OCaml builder: WhyMyMon (whymymon) + MonPoly/VeriMon (monpoly).
#           Also clones DejaVu so we can lift its shipped fat jar + wrappers.
###############################################################################
FROM ocaml/opam:alpine-3.20-ocaml-5.1 AS ocaml-builder

# linux-headers for eio's io_uring (uring) backend stubs
RUN sudo apk add --update --no-cache gmp-dev libffi-dev m4 perl pkgconfig git bash linux-headers
RUN sudo mkdir -p /usr/src/app && sudo chown opam:opam /usr/src/app

ARG WHYMYMON_BRANCH
ARG WHYMYMON_COMMIT
RUN git clone --branch "$WHYMYMON_BRANCH" https://github.com/nDylmer/whymymon.git /usr/src/app/whymymon \
    && if [ -n "$WHYMYMON_COMMIT" ]; then cd /usr/src/app/whymymon && git checkout "$WHYMYMON_COMMIT"; fi

WORKDIR /usr/src/app/whymymon

RUN opam init --disable-sandboxing -y && opam install dune -y

# WhyMyMon dependencies (unchanged from the upstream whymymon image).
RUN opam install dune menhir zarith \
      core_kernel base \
      core_unix.v0.16.0 \
      zarith_stubs_js.v0.16.1 \
      eio_main \
      js_of_ocaml js_of_ocaml-ppx

RUN mkdir -p /home/opam/dist && chown opam:opam /home/opam/dist

# Make the backend lookup paths ABSOLUTE. Upstream Monitor.exec_path
# (src/argument.ml) returns paths RELATIVE to the CWD — fine when you run
# whymymon from the repo root after third-party/download.sh, but in this image
# the monitors live at fixed /app/... locations while callers (e.g. an
# experiment driver) run whymymon from their own data dir. The relative lookup
# then fails with `realpath ENOENT third-party/timelymon/...` (whymymon.ml:118).
# Rewriting the three literals to /app makes "-path default" (and the implicit
# default when no -path is given) resolve from ANY working directory.
RUN sed -i \
      -e 's#"_build/install/default/bin/monpoly"#"/app/_build/install/default/bin/monpoly"#' \
      -e 's#"third-party/dejavu-online/out/dejavu-online"#"/app/third-party/dejavu-online/out/dejavu-online"#' \
      -e 's#"third-party/timelymon/target/release/timelymon"#"/app/third-party/timelymon/target/release/timelymon"#' \
      src/argument.ml

# --- WhyMyMon itself -> relocatable dist in /home/opam/dist ---
RUN eval $(opam env) && \
    dune build --profile=release @install && \
    dune install --prefix=/home/opam/dist --relocatable

# --- MonPoly / VeriMon ---------------------------------------------------------
# Same opam switch. Besides zarith (already present) monpoly's executable links
# dune-build-info (embeds version info) — a separate opam/findlib package.
# Installing it in its own layer keeps the big deps layer above cached.
# Produces _build/install/default/bin/monpoly inside its own tree.
ARG MONPOLY_COMMIT
RUN mkdir -p third-party && \
    git clone https://bitbucket.org/jshs/monpoly.git third-party/monpoly && \
    cd third-party/monpoly && git checkout "$MONPOLY_COMMIT"
#   libmonpoly is a sibling package in the same workspace (opam would install it
#   first); build BOTH packages in one go, else "-p monpoly" hides libmonpoly.
RUN opam install -y dune-build-info && \
    eval $(opam env) && cd third-party/monpoly && dune build -p libmonpoly,monpoly @install
#   Fallback if the package-restricted build ever misbehaves:
#     dune build --release src/main.exe   (binary -> _build/default/src/main.exe)

# --- DejaVu (online) -----------------------------------------------------------
# We ship its committed fat jar out/dejavu.jar + the out/dejavu-online wrapper.
# (Rebuilding from source needs the ancient sbt 0.13.16 / Scala 2.11.1 / JDK 8
#  toolchain — see the note at the bottom of this file. The shipped jar is the
#  project's own release artifact, so we use it directly.)
ARG DEJAVU_REPO
RUN git clone --depth 1 "$DEJAVU_REPO" third-party/dejavu-online

###############################################################################
# Stage 2 — Rust builder: TimelyMon. Built against musl so the binary runs on
#           the alpine runtime stage with no glibc.
###############################################################################
# NB: rust:1-alpine = latest stable 1.x. TimelyMon's dependency tree pulls
# crates that need the edition2024 cargo feature (stable since Rust 1.85), so
# the toolchain must be >= 1.85 even though Cargo.toml says rust-version 1.84.1.
FROM rust:1-alpine AS rust-builder
RUN apk add --no-cache musl-dev build-base git
ARG TIMELYMON_REPO
RUN git clone "$TIMELYMON_REPO" /usr/src/timelymon
WORKDIR /usr/src/timelymon
RUN cargo build --release --bin timelymon

###############################################################################
# Stage 3 — Runtime
###############################################################################
FROM alpine:3.20
ARG SCALA_VERSION

# gmp/libffi  : OCaml native stubs (zarith etc.) for whymymon + monpoly
# libgcc      : musl Rust binary (timelymon)
# bash        : the dejavu-online wrapper + scala/scalac launchers are bash
# openjdk8 +  : DejaVu *online* synthesises TraceMonitor.scala, then compiles
# Scala 2.11    (scalac) and runs (scala) it per formula AT RUN TIME — so the
#               full Scala 2.11 toolchain must be present, not just a JRE.
RUN apk add --update --no-cache gmp libffi libgcc bash ca-certificates openjdk8 \
 && wget -qO- "https://downloads.lightbend.com/scala/${SCALA_VERSION}/scala-${SCALA_VERSION}.tgz" \
      | tar xz -C /opt \
 && ln -s /opt/scala-${SCALA_VERSION}/bin/scala  /usr/local/bin/scala \
 && ln -s /opt/scala-${SCALA_VERSION}/bin/scalac /usr/local/bin/scalac

ENV JAVA_HOME=/usr/lib/jvm/java-1.8-openjdk
ENV PATH="$JAVA_HOME/bin:/usr/local/bin:$PATH"

# --- WhyMyMon binary (+ its relocatable stublibs) on PATH ---
COPY --from=ocaml-builder /home/opam/dist/bin/ /usr/local/bin/
COPY --from=ocaml-builder /home/opam/dist/lib/ /usr/local/lib/

# WhyMyMon writes each backend's translated formula to ./tmp/<formula> in the
# CWD but does NOT create that dir (src/monitor.ml). The experiment driver runs
# whymymon from arbitrary data dirs, so wrap the binary to `mkdir -p tmp` first.
# (written with printf, not a COPY heredoc, so it also builds on the legacy
#  non-BuildKit builder, which ignores `# syntax=` and rejects heredocs)
RUN mv /usr/local/bin/whymymon /usr/local/bin/whymymon.real \
 && printf '%s\n' \
      '#!/bin/sh' \
      'mkdir -p tmp 2>/dev/null || true' \
      'exec /usr/local/bin/whymymon.real "$@"' \
      > /usr/local/bin/whymymon \
 && chmod +x /usr/local/bin/whymymon

# --- The three monitors, placed at the exact exec_path locations under /app ---
WORKDIR /app

# MonPoly / VeriMon  ->  /app/_build/install/default/bin/monpoly
# (the installed bin/monpoly is a relative symlink to ../../../default/src/main.exe;
#  copy the concrete native binary to avoid COPY symlink ambiguity)
COPY --from=ocaml-builder \
     /usr/src/app/whymymon/third-party/monpoly/_build/default/src/main.exe \
     /app/_build/install/default/bin/monpoly

# DejaVu  ->  /app/third-party/dejavu-online/out/  (wrapper finds the jar via `dirname $0`)
COPY --from=ocaml-builder \
     /usr/src/app/whymymon/third-party/dejavu-online/out/dejavu-online \
     /usr/src/app/whymymon/third-party/dejavu-online/out/dejavu \
     /usr/src/app/whymymon/third-party/dejavu-online/out/dejavu.jar \
     /app/third-party/dejavu-online/out/

# TimelyMon  ->  /app/third-party/timelymon/target/release/timelymon
COPY --from=rust-builder /usr/src/timelymon/target/release/timelymon \
     /app/third-party/timelymon/target/release/timelymon

RUN chmod +x /app/_build/install/default/bin/monpoly \
             /app/third-party/dejavu-online/out/dejavu-online \
             /app/third-party/dejavu-online/out/dejavu \
             /app/third-party/timelymon/target/release/timelymon

RUN mkdir -p /app/tmp && chmod 777 /app/tmp

COPY --from=ocaml-builder /usr/src/app/whymymon/examples/ /app/examples/
COPY --from=ocaml-builder \
     /usr/src/app/whymymon/dejavu.sig \
     /usr/src/app/whymymon/dejavutest.mfotl \
     /usr/src/app/whymymon/dejavutest.timed.csv \
     /app/

CMD ["whymymon"]