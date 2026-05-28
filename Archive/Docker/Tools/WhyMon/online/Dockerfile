# Build stage
FROM ocaml/opam:alpine-ocaml-5.4 AS builder

RUN sudo apk add --update --no-cache gmp-dev libffi-dev m4 perl pkgconfig git bash musl-dev linux-headers gcc g++ make
RUN sudo mkdir -p /usr/src/app && sudo chown opam:opam /usr/src/app

ARG GIT_BRANCH=main
ARG GIT_COMMIT=""
RUN git clone --branch "$GIT_BRANCH" https://github.com/runtime-monitoring/whymon.git /usr/src/app/whymon \
    && if [ -n "$GIT_COMMIT" ]; then cd /usr/src/app/whymon && git checkout "$GIT_COMMIT"; fi

WORKDIR /usr/src/app/whymon

# Initialize OPAM and install dependencies
RUN opam init --disable-sandboxing -y && \
    eval $(opam env) && \
    opam update -y && \
    opam install -y dune && \
    opam install -y core_kernel base zarith menhir js_of_ocaml js_of_ocaml-ppx zarith_stubs_js

# Build in release mode
RUN eval $(opam env) && \
    dune build --profile=release @install -j$(nproc)

# Create output directory with proper permissions
RUN sudo mkdir -p /output && sudo chown opam:opam /output

# Copy binary and create static version
RUN mkdir -p /output && \
    cp _build/install/default/bin/whymon /output/whymon.dynamic && \
    cd /output && \
    # Try to create static binary using musl-gcc
    if command -v musl-gcc >/dev/null 2>&1; then \
        musl-gcc -static -o whymon /output/whymon.dynamic 2>/dev/null || \
        cp /output/whymon.dynamic /output/whymon; \
    else \
        cp /output/whymon.dynamic /output/whymon; \
    fi && \
    # Strip the binary
    strip /output/whymon 2>/dev/null || true && \
    echo "=== Binary Information ===" && \
    file /output/whymon && \
    ldd /output/whymon 2>&1 || echo "✓ Binary is static!"

FROM scratch
COPY --from=builder /output/whymon /tool
ENTRYPOINT ["tool"]
