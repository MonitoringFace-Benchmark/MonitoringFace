FROM alpine:3.19

WORKDIR /app
COPY driver/ /usr/local/bin/driver
COPY tool/ /usr/local/bin/tool
COPY data/ data/
COPY additional/ additional/

ENV PATH="/usr/local/bin:${PATH}"
ENTRYPOINT ["/bin/sh"]

