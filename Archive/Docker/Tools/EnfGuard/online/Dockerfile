# Build stage: Alpine 3.19, the base of the online image (OnlineExperimentTemplate),
# with its OCaml 4.14. opam has no core_unix >= v0.16 for Alpine >= 3.21, and
# v0.15 does not build against musl.
FROM alpine:3.19 AS builder

RUN apk add --no-cache ocaml ocaml-compiler-libs opam gmp-dev libffi-dev m4 perl pkgconfig git bash \
    musl-dev linux-headers gcc g++ make python3 cmake

ENV OPAMROOTISOK=1 OPAMYES=1
RUN opam init --bare --disable-sandboxing -a && opam switch create default ocaml-system

ARG GIT_BRANCH=enfguard
ARG GIT_COMMIT=""
RUN git clone --filter=blob:none --branch "$GIT_BRANCH" https://github.com/runtime-enforcement/whyenf.git /usr/src/app/whyenf \
    && if [ -n "$GIT_COMMIT" ]; then cd /usr/src/app/whyenf && git checkout "$GIT_COMMIT"; fi

WORKDIR /usr/src/app/whyenf

# Same dependency set as the offline image; their system packages are installed
# above (opam 2.1 misreads apk, hence --no-depexts)
RUN eval $(opam env) && \
    OPAMJOBS=$(nproc) opam install --no-depexts dune core_kernel core_unix base zarith menhir zarith_stubs_js qcheck pyml calendar z3

# MFOTL_lib lists z3 among its libraries, but no module uses it: link only
# the shared libraries the binary needs, so it runs where libz3 is absent
RUN eval $(opam env) && \
    OCAMLPARAM='_,ccopt=-Wl,--as-needed' dune build --profile=release bin/enfguard.exe -j$(nproc)

RUN mkdir -p /output && \
    cp _build/default/bin/enfguard.exe /output/enfguard && \
    strip /output/enfguard 2>/dev/null || true && \
    echo "=== Binary Information ===" && \
    ldd /output/enfguard 2>&1 && \
    if ldd /output/enfguard | grep -q libz3; then echo "enfguard still needs libz3" >&2; exit 1; fi

FROM scratch
COPY --from=builder /output/enfguard /tool
ENTRYPOINT ["tool"]
