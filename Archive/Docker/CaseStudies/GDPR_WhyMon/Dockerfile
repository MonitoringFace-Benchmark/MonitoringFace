FROM alpine:latest

RUN apk add --no-cache git tar

WORKDIR /data

RUN git clone https://github.com/runtime-enforcement/whyenf.git /tmp/whyenf && \
    cd /tmp/whyenf && \
    git checkout enfguard

CMD sh -c "\
mkdir -p data/Formula data/Signature data/Trace && \
cp -r /tmp/whyenf/examples/MonitoringFace/WhyMon/data/Formula/* data/Formula/ && \
cp -r /tmp/whyenf/examples/MonitoringFace/WhyMon/data/Signature/* data/Signature/ && \
cp -r /tmp/whyenf/examples/MonitoringFace/WhyMon/data/Trace/* data/Trace/ && \
cp /tmp/whyenf/examples/MonitoringFace/WhyMon/instructions.txt ."