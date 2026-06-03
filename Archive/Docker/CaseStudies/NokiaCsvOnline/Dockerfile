FROM alpine:latest

RUN apk add --no-cache git unzip bash

WORKDIR /data

RUN git clone https://github.com/LennardEc/nokia_online_log.git /tmp/nokia_online_log && \
    unzip /tmp/nokia_online_log/csv/Trace/ldcc_sample_csv.csv.zip -d /tmp/nokia_online_log/csv/Trace/ && \
    mv /tmp/nokia_online_log/csv/Trace/ldcc_sample_csv.csv /tmp/nokia_online_log/csv/Trace/trace.csv

CMD sh -c "\
mkdir -p data/Formula data/Signature data/Trace && \
cp -r /tmp/nokia_online_log/csv/Formula/* data/Formula/ && \
cp -r /tmp/nokia_online_log/csv/Signature/* data/Signature/ && \
cp /tmp/nokia_online_log/csv/Trace/trace.csv data/Trace/ && \
cp /tmp/nokia_online_log/csv/instructions.txt ."