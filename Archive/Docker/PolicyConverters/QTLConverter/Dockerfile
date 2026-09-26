FROM ubuntu:24.04


RUN apt-get update
RUN apt-get upgrade -y
RUN DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y git time openjdk-8-jdk scala 
RUN DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y adduser locales 
RUN DEBIAN_FRONTEND=noninteractive apt-get install --no-install-recommends -y maven

RUN adduser --disabled-password --gecos "" qtl-translator
RUN locale-gen en_US.UTF-8 &&\
    echo "export LANG=en_US.UTF-8 LANGUAGE=en_US.en LC_ALL=en_US.UTF-8" >> /home/qtl-translator/.bashrc

USER qtl-translator
ENV WDIR=/home/qtl-translator/work
WORKDIR /home/qtl-translator

# qtl-translator
ARG GIT_BRANCH=main
ARG GIT_COMMIT=""
RUN git clone --branch "$GIT_BRANCH" https://github.com/krledmno1/qtl-translator.git \
    && if [ -n "$GIT_COMMIT" ]; then git -C qtl-translator checkout "$GIT_COMMIT"; fi
RUN cd qtl-translator && \
    mvn clean package

RUN cp /home/qtl-translator/qtl-translator/target/spec-parser-1.0-SNAPSHOT.jar /home/qtl-translator/qtl-translator.jar
ADD qtl-translator.sh /home/qtl-translator/qtl-translator.sh
USER root
# strip CRs: from a CRLF (Windows) checkout the shebang reads "#!/bin/bash\r"
RUN sed -i 's/\r$//' /home/qtl-translator/qtl-translator.sh && \
    ln -s /home/qtl-translator/qtl-translator.sh /usr/local/bin/qtl-translator

USER qtl-translator
WORKDIR ${WDIR}

ENTRYPOINT ["qtl-translator"]