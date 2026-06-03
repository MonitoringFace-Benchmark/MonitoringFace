FROM alpine:latest

RUN apk add --no-cache git unzip bash

WORKDIR /data

RUN git clone https://github.com/LennardEc/nokia_online_log.git /tmp/nokia_online_log && \
    unzip /tmp/nokia_online_log/log/Trace/ldcc_sample_log.zip -d /tmp/nokia_online_log/log/Trace/ && \
    mv /tmp/nokia_online_log/log/Trace/ldcc_sample_log /tmp/nokia_online_log/log/Trace/trace.log

CMD sh -c "\
mkdir -p data/Formula data/Signature data/Trace && \
cp -r /tmp/nokia_online_log/log/Formula/* data/Formula/ && \
cp -r /tmp/nokia_online_log/log/Signature/* data/Signature/ && \
cp /tmp/nokia_online_log/log/Trace/trace.log data/Trace/ && \
cp /tmp/nokia_online_log/log/instructions.txt ."