# Build stage
FROM ocaml/opam:debian-12-ocaml-4.13 AS builder

RUN sudo apt-get update && sudo apt-get install -y \
    libgmp-dev libffi-dev m4 perl pkg-config git bash python3 \
    && sudo rm -rf /var/lib/apt/lists/*
RUN sudo mkdir -p /usr/src/app && sudo chown opam:opam /usr/src/app

ARG GIT_BRANCH=enfguard
RUN git clone --depth 1 --branch ${GIT_BRANCH} https://github.com/runtime-enforcement/whyenf.git /usr/src/app/whyenf

WORKDIR /usr/src/app/whyenf

# Initialize OPAM and install Dune first
RUN opam init --disable-sandboxing -y

# Create local install directory with proper permissions
RUN mkdir -p /home/opam/dist && chown opam:opam /home/opam/dist

# Install dependencies and build with local prefix
RUN opam switch create 4.13.1
RUN eval $(opam env --switch=4.13.1) && \
    opam install -y dune core_kernel core_unix base zarith menhir js_of_ocaml js_of_ocaml-ppx zarith_stubs_js qcheck pyml calendar z3 && \
    dune build --profile=release @install && \
    dune install --prefix=/home/opam/dist --relocatable

# Runtime stage
FROM debian:12-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    libgmp10 \
    libffi8 \
    time \
    && rm -rf /var/lib/apt/lists/*

# Copy installed binaries from builder stag
COPY --from=builder /home/opam/dist/bin/ /usr/local/bin/
COPY --from=builder /home/opam/dist/lib/ /usr/local/lib/

# Set the entry point
CMD ["enfguard"]
