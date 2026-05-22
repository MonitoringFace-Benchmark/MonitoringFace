FROM alpine:latest

RUN apk add --no-cache git tar

WORKDIR /data

RUN git clone https://bitbucket.org/jshs/monpoly.git /tmp/monpoly

CMD sh -c "\
cp -r /tmp/monpoly/examples/MonitoringFace/data . && \
cp -r /tmp/monpoly/examples/MonitoringFace/instructions.txt ."



