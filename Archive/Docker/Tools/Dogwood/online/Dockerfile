# Dogwood (https://github.com/dogwood-policy/dogwood) has no log-replaying
# front end of its own; the EnfFlash evaluation's `dogwood-enforce` replays
# MonPoly-format logs through Dogwood's reference authorizer, with the
# dogwood-language revision pinned in its Cargo.lock.
FROM rust:1 AS builder

ARG GIT_BRANCH=main
ARG GIT_COMMIT=""
RUN git clone --filter=blob:none --no-checkout --branch "$GIT_BRANCH" https://github.com/runtime-enforcement/EnfFlash.git /usr/src/enfflash \
    && cd /usr/src/enfflash \
    && git sparse-checkout set --no-cone /eval/enforcement/dogwood \
    && git checkout "${GIT_COMMIT:-HEAD}"

WORKDIR /usr/src/enfflash/eval/enforcement/dogwood

# Statically linked against glibc, so it runs in the (musl) online image: a
# musl build is markedly slower, its allocator dominating Dogwood's latency
RUN TARGET=$(rustc -vV | sed -n 's/^host: //p') && \
    RUSTFLAGS="-C target-feature=+crt-static" cargo build --release --locked --target "$TARGET" && \
    cp "target/$TARGET/release/dogwood-enforce" /dogwood-enforce && \
    strip /dogwood-enforce && \
    (ldd /dogwood-enforce 2>&1 || true)

FROM scratch
COPY --from=builder /dogwood-enforce /tool
ENTRYPOINT ["tool"]
