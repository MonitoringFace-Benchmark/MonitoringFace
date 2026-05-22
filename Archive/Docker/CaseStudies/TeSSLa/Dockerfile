FROM alpine:latest

RUN apk add --no-cache git unzip bash
WORKDIR /data
RUN git clone https://github.com/LennardEc/tessla_case_study.git /tmp/tessla_case_study

CMD sh -c "mkdir -p data/Policy data/Trace && cp -r /tmp/tessla_case_study/data/Policy/* data/Policy/ && \
cp /tmp/tessla_case_study/data/Trace/* data/Trace/ && cp /tmp/tessla_case_study/instructions.txt ."