# Build stage
FROM ocaml/opam:alpine-ocaml-5.4 AS builder

RUN sudo apk add --update --no-cache gmp-dev libffi-dev m4 perl pkgconfig git bash
RUN sudo mkdir -p /usr/src/app && sudo chown opam:opam /usr/src/app

ARG GIT_BRANCH=main
RUN git clone --depth 1 --branch $GIT_BRANCH https://github.com/runtime-monitoring/whymon.git /usr/src/app/whymon

WORKDIR /usr/src/app/whymon

# Initialize OPAM and install Dune first
RUN opam init --disable-sandboxing -y && opam install dune -y

# Create local install directory with proper permissions
RUN mkdir -p /home/opam/dist && chown opam:opam /home/opam/dist

# Install dependencies and build with local prefix
RUN opam install core_kernel base zarith menhir js_of_ocaml js_of_ocaml-ppx zarith_stubs_js && \
    eval $(opam env) && \
    dune build --profile=release @install && \
    dune install --prefix=/home/opam/dist --relocatable

# Runtime stage
FROM alpine:3.15

# Install runtime dependencies
RUN apk add --update --no-cache \
    gmp \
    libffi \
    time

# Copy installed binaries from builder stage
COPY --from=builder /home/opam/dist/bin/ /usr/local/bin/
COPY --from=builder /home/opam/dist/lib/ /usr/local/lib/

# Set the entry point
CMD ["whymon"]
