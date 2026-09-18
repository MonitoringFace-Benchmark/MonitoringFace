# Build stage
FROM ubuntu:24.04

RUN apt-get update
RUN apt-get upgrade -y
RUN DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y git time openjdk-8-jdk scala 
RUN DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y adduser locales 

RUN adduser --disabled-password --gecos "" dejavu
RUN locale-gen en_US.UTF-8 &&\
    echo "export LANG=en_US.UTF-8 LANGUAGE=en_US.en LC_ALL=en_US.UTF-8" >> /home/dejavu/.bashrc

USER dejavu
ENV WDIR=/home/dejavu/work
WORKDIR /home/dejavu

# DejaVu
# Honor a pinned commit: the image name carries it, so the build must too
# (the old clone silently built the branch HEAD regardless of GIT_COMMIT).
ARG GIT_BRANCH=master
ARG GIT_COMMIT=""
RUN git clone --branch "$GIT_BRANCH" https://github.com/havelund/dejavu.git \
    && if [ -n "$GIT_COMMIT" ]; then cd /home/dejavu/dejavu && git checkout "$GIT_COMMIT"; fi
RUN cp /home/dejavu/dejavu/out/artifacts/dejavu_jar/dejavu.jar /home/dejavu/dejavu.jar

COPY --chown=dejavu:dejavu build.sh /home/dejavu/build.sh
COPY --chown=dejavu:dejavu run.sh /home/dejavu/run.sh

USER root
RUN chmod 755 /home/dejavu/build.sh /home/dejavu/run.sh && \
    ln -s /home/dejavu/build.sh /usr/local/bin/build && \
    ln -s /home/dejavu/run.sh /usr/local/bin/run

USER dejavu
WORKDIR ${WDIR}

ENV PATH="/usr/local/bin:${PATH}"

CMD ["build"]