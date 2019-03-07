# AWS stack to renew Let's-encrypt-SSL-certificates

This repository provides an [Amazon AWS][Amazon AWS] **stack** to periodically and automatically renew a Let's-encrypt-SSL-certificate, and to deploy it for a website hosted on [Amazon S3][Amazon S3].

The stack consists of:

  * the required [AWS IAM][AWS IAM] **users**, **roles** and their associated **policies**
  * an [Amazon ECR][Amazon ECR] **repository** which holds a docker image with the certificate renewal script
  * an [Amazon ECS][Amazon ECS] **task definition** which describes the task to renew a certificate
  * an [Amazon ECS][Amazon ECS] **cluster** where AWS will create a docker container from the supplied docker image
  * an [Amazon Lambda][Amazon Lambda] **function**  which will launch the ECS task
  * an [Amazon CloudWatch][Amazon CloudWatch] **log group** which collects the logs of the docker container and the Lambda function
  * an [Amazon CloudWatch][Amazon CloudWatch] **log group** which collects the logs of the docker container and the Lambda function
  * a [Amazon CloudWatch][Amazon CloudWatch] **event rule** which periodically (once a month) triggers the lambda function to renew the certificate


The required stack is managed with [ansible](https://www.ansible.com/) playbooks.

## Configuration

### Configure the AWS credentials

  * copy `aws.env.distrib` to `aws.env` and update the environment variables in `aws.env`
  * set the required configuration values

    ```bash
    $ source aws.env
    ```

### Configure the stack

  * copy `ansible/config.yml.distrib` to `ansible/config.yml` and update the configuration entries


## Manage the stack

### Create the stack

  ```bash
  $ cd ansible
  # creates the AWS stack 
  $ ansible-playbook create-stack.yml
  ```

### Delete the stack

  ```bash
  $ cd ansible
  $ ansible-playbook delete-stack.yml
  ```

[Amazon AWS]: https://aws.amazon.com
[Amazon ECS]: https://aws.amazon.com/ecs/
[Amazon ECR]: https://aws.amazon.com/ecr/
[AWS IAM]: https://aws.amazon.com/iam/
[Amazon CloudFormation]: https://aws.amazon.com/cloudformation/
[Amazon Lambda]: https://aws.amazon.com/lambda/
[Amazon CloudWatch]: https://aws.amazon.com/cloudwatch/
[Amazon CloudFormation]: https://aws.amazon.com/cloudformation/
[AWS CLI]: https://aws.amazon.com/cli/
[Amazon VPC]: https://aws.amazon.com/vpc/
[Amazon S3]: https://aws.amazon.com/s3/