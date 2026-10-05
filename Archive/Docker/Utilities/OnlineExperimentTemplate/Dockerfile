FROM alpine:3.19

RUN apk add --no-cache gmp libffi ca-certificates python3 && ln -sf /usr/bin/python3 /usr/local/bin/python3 && python3 --version

WORKDIR /app
COPY driver/ /usr/local/bin/driver
COPY tool/ /usr/local/bin/tool
COPY data/ data/
COPY additional/ additional/

# the Python packages the policy's functions import (its requirements file, in
# additional/); packages without a musl wheel are built here, with a toolchain
# that is removed again
ARG POLICY_REQUIREMENTS=""
RUN if [ -n "$POLICY_REQUIREMENTS" ]; then \
        apk add --no-cache py3-pip libgomp libstdc++ && \
        apk add --no-cache --virtual .policy-build build-base python3-dev linux-headers && \
        pip install --no-cache-dir --break-system-packages -r "additional/$POLICY_REQUIREMENTS" && \
        apk del .policy-build; \
    fi
COPY processors/ processors/

ENV PATH="/usr/local/bin:${PATH}"
ENTRYPOINT ["/usr/local/bin/driver"]
