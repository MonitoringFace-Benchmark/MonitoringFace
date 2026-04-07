FROM ocaml/opam:alpine-ocaml-4.14 AS builder

RUN sudo apk add --update --no-cache gmp-dev libffi-dev m4 perl pkgconfig git bash musl-dev linux-headers gcc g++ make

WORKDIR /home/opam

ARG GIT_BRANCH=main
ARG GIT_COMMIT=""

RUN git clone --branch "$GIT_BRANCH" https://github.com/LennardEc/monpoly_fork.git /home/opam/monpoly && \
    if [ -n "$GIT_COMMIT" ]; then cd /home/opam/monpoly && git checkout "$GIT_COMMIT"; fi

WORKDIR /home/opam/monpoly

# Create proper dune-workspace file with language declaration
RUN cat > dune-workspace << 'EOF'
(lang dune 3.0)
(env
 (release
  (flags
   (:standard -w -8-11-20-26)))
 (default
  (flags
   (:standard -w -8-11-20-26))))
EOF

RUN opam init --disable-sandboxing -y && \
    eval $(opam env) && \
    opam update -y && \
    opam install -y dune && \
    opam install -y . --deps-only

# Build once, from a verified dune workspace root
RUN eval $(opam env) && \
    pwd && ls -la && \
    test -f dune-project -o -f dune-workspace && \
    dune build --profile=release @install -j$(nproc)

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