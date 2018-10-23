#!/bin/bash

# remove the certbot challenge 
aws s3 rm s3://www.kacon.ch/.well-known/acme-challenge/$CERTBOT_TOKEN
