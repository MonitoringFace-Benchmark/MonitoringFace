# Multi-arch compatible Dockerfile
FROM rust:1.84.1-alpine as builder

RUN apk add --no-cache musl-dev openssl-dev openssl-libs-static git pkgconfig make gcc
RUN rustup set auto-self-update disable && rustup install nightly --profile minimal && rustup default nightly

# Add both architecture targets
RUN rustup target add x86_64-unknown-linux-musl aarch64-unknown-linux-musl

ARG GIT_BRANCH=development
ARG GIT_COMMIT=""
ARG TARGETARCH

# Set target based on build architecture
RUN if [ -z "$TARGETARCH" ]; then \
        TARGETARCH=$(uname -m); \
    fi && \
    case "$TARGETARCH" in \
        amd64|x86_64) RUST_TARGET="x86_64-unknown-linux-musl" ;; \
        arm64|aarch64) RUST_TARGET="aarch64-unknown-linux-musl" ;; \
        *) echo "Unsupported architecture: $TARGETARCH"; exit 1 ;; \
    esac && \
    echo "Building for $RUST_TARGET" && \
    echo "RUST_TARGET=$RUST_TARGET" >> /tmp/env

RUN git clone --branch ${GIT_BRANCH} --recurse-submodules https://git.ku.dk/kfx532/timelymon.git /usr/src/app/timelymon \
    && cd /usr/src/app/timelymon && if [ -n "${GIT_COMMIT}" ]; then git checkout ${GIT_COMMIT}; fi && git submodule update --init --recursive

WORKDIR /usr/src/app/timelymon

# Build for the detected target
RUN . /tmp/env && \
    cargo build --release --target ${RUST_TARGET} --bin timelymon && \
    cp target/${RUST_TARGET}/release/timelymon /timelymon

FROM scratch
COPY --from=builder /timelymon /tool
ENTRYPOINT ["/tool"]