#!/bin/bash
#
# generates a new let's encrypt certificate, deploys it as AWS server
# certificate, and assigns it to the AWS cloudfront distribution for
# www.kacon.ch


# create the certificate
certbot certonly \
    --manual \
    --domains www.kacon.ch \
    --email "karl.guggisberg@kacon.ch" \
    --preferred-challenges http \
    --manual-public-ip-logging-ok \
    --no-eff-email \
    --agree-tos \
    --manual-auth-hook /certificate-renewal/certbot-auth-hook.sh \
    --manual-cleanup-hook /certificate-renewal/certbot-cleanup-hook.sh

CERTIFICATE_NAME=cert_www_kacon_ch_$(date '+%Y-%m-%dT%H-%M-%S')
echo "Uploading the new server certificate '$CERTIFICATE_NAME' ..."

CERTIFICATE_ID=$(aws iam upload-server-certificate \
  --server-certificate-name $CERTIFICATE_NAME \
  --private-key file:///etc/letsencrypt/live/www.kacon.ch/privkey.pem \
  --certificate-body file:///etc/letsencrypt/live/www.kacon.ch/fullchain.pem \
  --path /cloudfront/certs/ \
  | jq -r ".ServerCertificateMetadata.ServerCertificateId")

echo "Certificate uploaded. Certificate ID is '$CERTIFICATE_ID'"


#TODO: configure the production distribution
# E2GEKJ7CN252O3 is a test distribution
CLOUDFRONT_DISTRIBUTION_ID=E2GEKJ7CN252O3

echo "Get cloudfront distribution $CLOUDFRONT_DISTRIBUTION_ID ..."
aws cloudfront get-distribution-config \
    --id $CLOUDFRONT_DISTRIBUTION_ID \
    > $CLOUDFRONT_DISTRIBUTION_ID.current.json

ETAG=$(jq -r '.ETag' $CLOUDFRONT_DISTRIBUTION_ID.current.json)

jq --arg CERTIFICATE_ID "$CERTIFICATE_ID" '
    .DistributionConfig.ViewerCertificate={
        "IAMCertificateId": $CERTIFICATE_ID,
        "SSLSupportMethod": "sni-only",
        "MinimumProtocolVersion": "TLSv1.1_2016",
        "Certificate": $CERTIFICATE_ID,
        "CertificateSource": "iam"
    } | .DistributionConfig ' \
    $CLOUDFRONT_DISTRIBUTION_ID.current.json \
    > $CLOUDFRONT_DISTRIBUTION_ID.updated.json

echo "Update cloudfront distribution $CLOUDFRONT_DISTRIBUTION_ID ..."
aws cloudfront update-distribution \
    --id $CLOUDFRONT_DISTRIBUTION_ID \
    --if-match $ETAG \
    --distribution-config file://$CLOUDFRONT_DISTRIBUTION_ID.updated.json

