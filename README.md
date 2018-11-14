# AWS stack

Automatic renewal of a let's encrypt runs on an _AWS stack_, which consists of 

  * the required AWS IAM **users**, **roles** and their associated **policies**
  * an AWS ECR **repository** which holds a docker images with the renewal script
  * an AWS ECS **task definition** which describes the task to renew a certificate
  * an AWS CloudWatch **log group** which collects the logs from running the tag and where the logs can be consulted
  * an AWS ECS **cluster** where the job is run

The required stack can be created with an AWS CloudFormation template, except the required AWS ECS **cluster** which is
not created as part of the stack. The certificate renewal task uses the default ECS cluster of type FARGATE, i.e. a cluster based on Amazons internal compute engines and not on a set of AWS ECS engines we launch ourselves.

## Manage the stack

The stack is described in the AWS CloudFormation template `cloudformation/certificate-renewal-stack.yml`.

Create the stack with the following command:

```bash

$ cd cloudformation

# create the stack 
$ aws cloudformation create-stack \
  --profile root \
  --capabilities CAPABILITY_NAMED_IAM  \
  --stack-name certificate-renewal-stack \
  --template-body file://certificate-renewal-stack.yml
```

Open the [AWS CloudFormation console](https://eu-central-1.console.aws.amazon.com/cloudformation/) to
observe how the stack is created and whether it is created successfully.

To delete the stack run:

```bash
$ aws cloudformation delete-stack \
  --profile root \
  --stack-name certificate-renewal-stack
```

## Manage the cluster

```bash
$ aws ecs list-clusters \
    --profile root
```

If the output looks as follows, you already have a default cluster. 
```json
{
    "clusterArns": [
        "arn:aws:ecs:eu-central-1:154819770423:cluster/default"
    ]
}
```

If there's no entry `...:cluster/default` in the list, then you should create the cluster with 
the following command:

```bash
$ aws ecs create-cluster \
  --profile root \
  --cluster default
```

To delete the cluster, run:

```bash
$ aws ecs delete-cluster \
  --profile root \
  --cluster default
```

# Docker container

A shell script requests a new certificate from the _let's encrypt_ servers, uploads to the AWS infrastructure and attaches it to the AWS CloudFront distribution. The script and and its required resources are assembled in docker image.


## create the docker image

```bash
$ cd docker 

# build the container
$ sudo docker build \
  --tag certificate-renewal \
  --file certificate-renewal.docker .

# tag it. Necessary to upload it later to the AWS ECS repository
# 154819770423.dkr.ecr.eu-central-1.amazonaws.com/certificate-renewal is the repositoryUri
# of the repository the docker image is pushed to.
# 
$ sudo docker tag certificate-renewal 154819770423.dkr.ecr.eu-central-1.amazonaws.com/certificate-renewal
```

## upload docker image to AWS ECR repository

The docker images `certificate-renewal` must be pushed to the AWS ECS repository `certificate-renewal`. 

First, get login credentials for docker and login using docker:
```bash
# get the login
$ aws ecr get-login \
  --profile root \
  --no-include-email

# run the login command 
$ sudo docker login .... # this is the output of the last command
```
The upload the docker images:

```bash
# upload the docker images
$ sudo docker push 154819770423.dkr.ecr.eu-central-1.amazonaws.com/certificate-renewal


```
## run docker container locally
```bash
$  sudo docker run \
    -ti \
    --rm \
    -e "AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID" \
    -e "AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY" \
    -e "AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION" \
    certificate-renewal bash
```

# IAM

* role `certificateRenewalRole`

  * attached policies

    * AmazonEC2ContainerServiceforEC2Role
    * AmazonSSMReadParameter  - to read SSM system parameters
    * KaconChWriteCertbotChallenge          - write to S3 bucket for certbot challenge
    * KaconChUpdateCloudfontDistribution   - update cloud front distribution for kacon.ch

* group `certificate-renewer`

  * attached policies
    * AmazonSSMReadParameter  - to read SSM system parameters
    * KaconChS3Write          - write to S3 bucket for kacon.ch website
    * KaconChUpdateCloudfontDistribution   - update cloud front distribution for kacon.ch


* user `certificate-renewer`

    * member of group `certificate-renewer`

From the dev host, login with `certificate-renewer` and test. When executing an AWS lambda function or an ECS task,
use the `certificateRenewalRole`.


{"Version":"2012-10-17","Statement":[{"Sid":"VisualEditor0","Effect":"Allow","Action":["s3:PutObject","s3:GetObject"],"Resource":"arn:aws:s3:::www.kacon.ch/.well-known/acme-challenge/*"}]}

```bash
# creates the policy KaconChWriteCertbotChallenge
$ aws iam create-policy \
    --profile root \
    --policy-name "KaconChWriteCertbotChallenge" \
    --description "Allows to create certbot challenges in the S3 bucket hosting www.kacon.ch" \
    --policy-document '{"Version":"2012-10-17","Statement":[{"Sid":"VisualEditor0","Effect":"Allow","Action":["s3:PutObject","s3:GetObject"],"Resource":"arn:aws:s3:::www.kacon.ch/.well-known/acme-challenge/*"}]}'

# create group
$ aws iam create-group \
    --profile root \
    --group-name certificate-renewer-group

$ aws iam attach-group-policy \
    --profile root \
    --group-name certificate-renewer-group \
    --policy-arn "arn:aws:iam::154819770423:policy/KaconChWriteCertbotChallenge"

$ aws iam create-user \
    --profile root \
    --user-name certificate-renewer


$ aws iam add-user-to-group \
    --profile root \
    --group-name certificate-renewer-group \
    --user-name certificate-renewer


$ aws iam remove-user-from-group \
    --profile root \
    --group-name certificate-renewer-group \
    --user-name certificate-renewer

$ aws iam delete-user \
    --profile root \
    --user-name certificate-renewer

$ aws iam detach-group-policy \
    --profile root \
    --group-name certificate-renewer-group \
    --policy-arn "arn:aws:iam::154819770423:policy/KaconChWriteCertbotChallenge"

$ aws iam delete-group \
    --profile root \
    --group-name certificate-renewer-group
```


# Docker 

## create docker image

```bash
# build the container
$ sudo docker build -t certificate-renewal -f certificate-renewal.docker .

# tag it. Necessary to upload it later to the AWS ECS repository
$ sudo docker tag certificate-renewal 154819770423.dkr.ecr.eu-central-1.amazonaws.com/certificate-renewal
```

## run docker container locally

```bash
$  sudo docker run \
    -ti \
    --rm \
    -e "AWS_ACCESS_KEY_ID=$AWS_ACCESS_KEY_ID" \
    -e "AWS_SECRET_ACCESS_KEY=$AWS_SECRET_ACCESS_KEY" \
    -e "AWS_DEFAULT_REGION=$AWS_DEFAULT_REGION" \
    certificate-renewal bash
```

## upload docker image to AWS ECS repository
```bash
# get the login
$ aws ecr get-login \
  --profile root \
  --no-include-email

# run the login command
$ sudo docker login ...

# upload the docker images
$ sudo docker push 154819770423.dkr.ecr.eu-central-1.amazonaws.com/certificate-renewal

```

# Lambda

# create the zip file with the lambda code

```bash
$ npm run assemble

```
```bash
# create the lambda function
$ aws lambda create-function \
  --profile root \
  --function-name CertificateRenewal \
  --runtime nodejs8.10 \
  --role arn:aws:iam::154819770423:role/hello-world-role \
  --zip-file fileb://certificate-renewal.zip \
  --handler certificate-renewal.handler \
  --description "Automatically renews a let's encrypt certificate"

# update the code
$ aws lambda update-function-code \
    --profile root \
    --function-name  CertificateRenewal \
    --zip-file fileb://certificate-renewal.zip

# invoke the function
$ aws lambda invoke \
  --profile root \
  --function-name CertificateRenewal \
  certificate-renewal.output
```

# Cloudformation

```bash
$ aws cloudformation create-stack \
  --profile root \
  --capabilities CAPABILITY_NAMED_IAM  \
  --stack-name certificate-renewal-stack \
  --template-body file://certificate-renewal-stack.yml

$ aws cloudformation update-stack \
  --profile root \
  --capabilities CAPABILITY_NAMED_IAM \
  --stack-name certificate-renewal-stack \
  --template-body file://certificate-renewal-stack.yml

$ aws cloudformation validate-template \
  --profile root \
  --template-body file://certificate-renewal-stack.yml


$ aws cloudformation describe-stacks \
  --profile root \
  --stack-name certificate-renewal-stack


$ aws cloudformation delete-stack \
  --profile root \
  --stack-name certificate-renewal-stack
```

# Certbot

## Manual steps

```bash
# --non-interactive?
$ certbot certonly \
    --manual \
    --preferred-challenges http \
    --email "karl.guggisberg@kacon.ch" \
    --domains www.kacon.ch \
    --manual-public-ip-logging-ok \
    --no-eff-email \
    --agree-tos \
    --manual-auth-hook /certificate-renewal/certbot-authenticator.sh
```