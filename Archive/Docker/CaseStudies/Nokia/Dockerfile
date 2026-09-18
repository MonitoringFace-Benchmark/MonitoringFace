FROM alpine:latest

RUN apk add --no-cache git unzip bash

WORKDIR /data

ARG GIT_BRANCH=main
ARG GIT_COMMIT=""
RUN git clone --branch "$GIT_BRANCH" https://github.com/LennardEc/nokia_case_study.git /tmp/nokia_case_study && \
    if [ -n "$GIT_COMMIT" ]; then git -C /tmp/nokia_case_study checkout "$GIT_COMMIT"; fi && \
    unzip /tmp/nokia_case_study/data/Trace/trace.csv.zip -d /tmp/nokia_case_study/data/Trace/

CMD sh -c "\
mkdir -p data/Formula data/Signature data/Trace && \
cp -r /tmp/nokia_case_study/data/Formula/* data/Formula/ && \
cp -r /tmp/nokia_case_study/data/Signature/* data/Signature/ && \
cp /tmp/nokia_case_study/data/Trace/trace.csv data/Trace/ && \
cp /tmp/nokia_case_study/instructions.txt ."
