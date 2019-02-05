#
# creates a docker image for renewing the certificate
#
FROM ubuntu:18.04

# install required utilities
# TODO(karl): remove.not needed anymore for the python script
#RUN apt-get update && apt-get install -y \
#  curl \
#  jq

# install pip and python3 modules
RUN apt-get -y update
RUN apt-get install -y \
        python3 \
        python3-pip 
RUN pip3 install --upgrade pip
RUN pip3 install \
        request \
        boto3
RUN apt-get clean

# install awscli using pip
RUN pip3 --no-cache-dir install --upgrade awscli

ENV DEBIAN_FRONTEND=noninteractive

# install certbot
RUN apt-get update \
    && apt-get -y install software-properties-common \
    && add-apt-repository -y ppa:certbot/certbot \
    && apt-get update \
    && apt-get -y install certbot

RUN mkdir -p /certificate-renewal
COPY bin/renew-certificate.py /certificate-renewal





