# OOOMon online: same verified binary; reads the token stream from stdin when
# no -log is given, so the online driver can pipe events into the container.
# Built on Alpine (musl) because the online driver image is Alpine-based and
# runs the binary extracted from this image; the final stage is a bare
# `scratch` carrier holding /tool, matching the extraction convention of the
# other online tools.
FROM ocaml/opam:alpine-ocaml-4.14 AS builder

USER root
RUN apk add --no-cache git gmp-dev m4 musl-dev gcc make perl pkgconfig
USER opam

RUN opam install -y ocamlfind zarith stdlib-shims

ARG GIT_BRANCH=ooomon_rework
ARG GIT_COMMIT=""
RUN git clone --branch ${GIT_BRANCH} https://git.ku.dk/krq770/formalized_streaming_monitor.git /home/opam/ooomon \
    && cd /home/opam/ooomon && if [ -n "${GIT_COMMIT}" ]; then git checkout ${GIT_COMMIT}; fi

WORKDIR /home/opam/ooomon/frontend
RUN eval $(opam env) && ./build.sh

FROM scratch
COPY --from=builder /home/opam/ooomon/frontend/ooomon /tool
ENTRYPOINT ["/tool"]
