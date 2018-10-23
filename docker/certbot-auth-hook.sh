#!/bin/bash
echo "CERTBOT_VALIDATION: $CERTBOT_VALIDATION"
echo "CERTBOT_TOKEN: $CERTBOT_TOKEN"

mkdir -p /certificate-renewal/challenges
echo $CERTBOT_VALIDATION > /certificate-renewal/challenges/$CERTBOT_TOKEN
aws s3 cp /certificate-renewal/challenges/$CERTBOT_TOKEN s3://www.kacon.ch/.well-known/acme-challenge/$CERTBOT_TOKEN
sleep 5