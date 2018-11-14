# AWS stack

This repository provices an [Amazon CloudFormation][Amazon CloudFormation] **stack** to periodically and automatically renew a Let's-encrypt-SSL-certificate and to configure and deploy it for a website hosted on [Amazon S3][Amazon S3].

The stack consists of:

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
  --capabilities CAPABILITY_NAMED_IAM  \
  --stack-name certificate-renewal-stack \
  --template-body file://certificate-renewal-stack.yml
```

Open the [AWS CloudFormation console](https://eu-central-1.console.aws.amazon.com/cloudformation/) to
observe how the stack is created and whether it is created successfully.

To delete the stack run:

```bash
$ aws cloudformation delete-stack \
  --stack-name certificate-renewal-stack
```

## Manage the cluster

```bash
$ aws ecs list-clusters
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
$ aws ecs create-cluster --cluster default
```

To delete the cluster, run:

```bash
$ aws ecs delete-cluster --cluster default
```

# Docker container

A shell script requests a new certificate from the _let's encrypt_ servers, uploads to the AWS infrastructure and attaches it to the AWS CloudFront distribution. The script and and its required resources are assembled in docker image.

