FROM alpine:3.19

RUN apk add --no-cache gmp libffi ca-certificates python3 && ln -sf /usr/bin/python3 /usr/local/bin/python3 && python3 --version

WORKDIR /app
COPY driver/ /usr/local/bin/driver
COPY tool/ /usr/local/bin/tool
COPY data/ data/
COPY additional/ additional/

ENV PATH="/usr/local/bin:${PATH}"
ENTRYPOINT ["/usr/local/bin/driver"]
