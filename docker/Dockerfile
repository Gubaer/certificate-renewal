#
# creates a sample docker image to test the AWS container registry
#
FROM ubuntu:18.04

# install required utilities
RUN apt-get update && apt-get install -y \
  curl \
  jq

# install pip
RUN apt-get update && \
    apt-get install -y \
        python3 \
        python3-pip \
        python3-setuptools \
        groff \
        less \
    && pip3 install --upgrade pip \
    && apt-get clean

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
COPY renew.sh /certificate-renewal/renew.sh
COPY certbot-auth-hook.sh /certificate-renewal/certbot-auth-hook.sh
COPY certbot-cleanup-hook.sh /certificate-renewal/certbot-cleanup-hook.sh
RUN chmod +x /certificate-renewal/*.sh





