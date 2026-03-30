FROM alpine:3.19

RUN apk add --no-cache gmp libffi ca-certificates

WORKDIR /app
COPY driver/ /usr/local/bin/driver
COPY tool/ /usr/local/bin/tool
COPY data/ data/
COPY additional/ additional/

ENV PATH="/usr/local/bin:${PATH}"
ENTRYPOINT ["/usr/local/bin/driver"]
