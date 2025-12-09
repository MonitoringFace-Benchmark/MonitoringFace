FROM rust:1.84.1 as builder
RUN rustup install nightly
RUN rustup default nightly

RUN apt-get update && apt-get install -y pkg-config libssl-dev git && rm -rf /var/lib/apt/lists/*

ARG GIT_BRANCH=RV24_Tool_Paper
RUN git clone --branch ${GIT_BRANCH} --recurse-submodules https://git.ku.dk/kfx532/timelymon.git /usr/src/app/timelymon

WORKDIR /usr/src/app/timelymon
RUN cargo build --release --bin timelymon && cp target/release/timelymon /usr/local/bin/timelymon

# Use bookworm instead of bullseye for runtime
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y libssl3 ca-certificates time && rm -rf /var/lib/apt/lists/*
COPY --from=builder /usr/local/bin/timelymon /usr/local/bin/
CMD ["timelymon"]
