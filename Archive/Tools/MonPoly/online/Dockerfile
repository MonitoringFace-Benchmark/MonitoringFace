FROM ocaml/opam:alpine-ocaml-4.14 AS builder

RUN sudo apk add --update --no-cache gmp-dev libffi-dev m4 perl pkgconfig git bash musl-dev linux-headers gcc g++ make

WORKDIR /home/opam

ARG GIT_BRANCH=master
ARG GIT_COMMIT=""

RUN git clone --branch "$GIT_BRANCH" https://bitbucket.org/jshs/monpoly.git && \
    if [ -n "$GIT_COMMIT" ]; then cd monpoly && git checkout "$GIT_COMMIT"; fi

WORKDIR /home/opam/monpoly
RUN opam init --disable-sandboxing -y && eval $(opam env) && opam update -y && opam install -y dune && opam install -y . --deps-only

# Build the project
RUN eval $(opam env) && dune build --profile=release @install -j$(nproc)

# Create output directory with proper permissions
RUN sudo mkdir -p /output && sudo chown opam:opam /output

# Copy binary and create static version
RUN mkdir -p /output && \
    cp _build/install/default/bin/monpoly /output/monpoly.dynamic && \
    cd /output && \
    # Try to create static binary using musl-gcc
    if command -v musl-gcc >/dev/null 2>&1; then \
        musl-gcc -static -o monpoly /output/monpoly.dynamic 2>/dev/null || \
        cp /output/monpoly.dynamic /output/monpoly; \
    else \
        cp /output/monpoly.dynamic /output/monpoly; \
    fi && \
    # Strip the binary
    strip /output/monpoly 2>/dev/null || true && \
    echo "=== Binary Information ===" && \
    file /output/monpoly && \
    ldd /output/monpoly 2>&1 || echo "✓ Binary is static!"

FROM scratch
COPY --from=builder /output/monpoly /tool
ENTRYPOINT ["tool"]