FROM alpine:latest

RUN apk add --no-cache git unzip bash
WORKDIR /data
ARG GIT_BRANCH=main
ARG GIT_COMMIT=""
RUN git clone --branch "$GIT_BRANCH" https://github.com/LennardEc/tessla_case_study.git /tmp/tessla_case_study \
    && if [ -n "$GIT_COMMIT" ]; then git -C /tmp/tessla_case_study checkout "$GIT_COMMIT"; fi

CMD sh -c "mkdir -p data/Policy data/Trace && cp -r /tmp/tessla_case_study/data/Policy/* data/Policy/ && \
cp /tmp/tessla_case_study/data/Trace/* data/Trace/ && cp /tmp/tessla_case_study/instructions.txt ."