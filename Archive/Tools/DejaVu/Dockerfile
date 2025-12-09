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
RUN git clone https://github.com/havelund/dejavu.git
RUN cp /home/dejavu/dejavu/out/artifacts/dejavu_jar/dejavu.jar /home/dejavu/dejavu.jar
ADD dejavu.sh /home/dejavu/dejavu.sh
USER root
RUN ln -s /home/dejavu/dejavu.sh /usr/local/bin/dejavu

USER dejavu
WORKDIR ${WDIR}

ENTRYPOINT ["dejavu"]