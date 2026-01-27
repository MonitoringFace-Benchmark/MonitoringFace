FROM alpine:latest

RUN apk add --no-cache git tar

WORKDIR /data

RUN git clone https://github.com/runtime-enforcement/whyenf.git /tmp/whyenf && \
    cd /tmp/whyenf && \
    git checkout enfguard && \
    cp -r examples/MonitoringFace /data && \
    rm -rf /tmp/whyenf

