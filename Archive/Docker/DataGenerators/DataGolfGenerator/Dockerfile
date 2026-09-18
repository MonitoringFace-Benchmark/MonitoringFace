# =========================
# Build stage
# =========================
FROM ocaml/opam:alpine-ocaml-4.14 AS builder

# Switch to root to install system packages
USER root
RUN echo "http://dl-cdn.alpinelinux.org/alpine/edge/community" >> /etc/apk/repositories && \
    apk update && apk add --no-cache gmp gmp-dev libffi libffi-dev m4 perl pkgconfig git bash sudo

# Prepare app directory
RUN mkdir -p /usr/src/app && chown opam:opam /usr/src/app
USER opam

# Clone the project
ARG GIT_BRANCH=main
ARG GIT_COMMIT=""
RUN git clone --branch "$GIT_BRANCH" https://git.ku.dk/krq770/minidatagolf.git /usr/src/app/monpoly \
    && if [ -n "$GIT_COMMIT" ]; then git -C /usr/src/app/monpoly checkout "$GIT_COMMIT"; fi
WORKDIR /usr/src/app/monpoly

# Initialize OPAM and install Dune
RUN opam init --disable-sandboxing -y && opam install dune -y

# Install OCaml dependencies
RUN eval $(opam env) && opam install qcheck zarith bisect_ppx landmarks-ppx -y

# Pin local packages
RUN eval $(opam env) && \
    opam pin add -n libmonpoly . -y && \
    opam pin add -n monpoly . -y && \
    opam pin add -n monpoly-tools . -y && \
    opam install libmonpoly --deps-only -y && \
    opam install monpoly --deps-only -y && \
    opam install monpoly-tools --deps-only -y

# Build monpoly
RUN eval $(opam env) && \
    dune build --profile=release @install && \
    dune install --prefix=/home/opam/dist --relocatable

# Build datagolf
RUN eval $(opam env) && dune build datagolf/bin/main.exe

# Copy datagolf executable to dist
RUN mkdir -p /home/opam/dist/bin && \
    cp _build/default/datagolf/bin/main.exe /home/opam/dist/bin/datagolf

# =========================
# Runtime stage
# =========================
FROM alpine:3.15

# Runtime dependencies
RUN apk add --update --no-cache gmp libffi bash

# Copy installed binaries and libraries from builder
COPY --from=builder /home/opam/dist/bin/ /usr/local/bin/
COPY --from=builder /home/opam/dist/lib/ /usr/local/lib/

# Copy datagolf examples folder
COPY --from=builder /usr/src/app/monpoly/datagolf/examples /usr/local/bin/examples

WORKDIR /usr/local/bin

# Default command
CMD ["datagolf"]
