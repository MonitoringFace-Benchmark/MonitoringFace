FROM alpine:latest

RUN apk add --no-cache git unzip bash

WORKDIR /data

ARG GIT_BRANCH=main
ARG GIT_COMMIT=""
RUN git clone --branch "$GIT_BRANCH" https://github.com/LennardEc/nokia_online_log.git /tmp/nokia_online_log && \
    if [ -n "$GIT_COMMIT" ]; then git -C /tmp/nokia_online_log checkout "$GIT_COMMIT"; fi && \
    unzip /tmp/nokia_online_log/log/Trace/ldcc_sample_log.zip -d /tmp/nokia_online_log/log/Trace/ && \
    mv /tmp/nokia_online_log/log/Trace/ldcc_sample_log /tmp/nokia_online_log/log/Trace/trace.log

CMD sh -c "\
mkdir -p data/Formula data/Signature data/Trace && \
cp -r /tmp/nokia_online_log/log/Formula/* data/Formula/ && \
cp -r /tmp/nokia_online_log/log/Signature/* data/Signature/ && \
cp /tmp/nokia_online_log/log/Trace/trace.log data/Trace/ && \
cp /tmp/nokia_online_log/log/instructions.txt ."