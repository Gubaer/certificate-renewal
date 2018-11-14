
# Prepare and upload a simple docker images

```bash
# create the docker image
$ sudo docker build -t hello-world -f hello-world.docker .
```

To access the Amazon ECR services
* create an IAM user (in my case: `kacon-ch-certificate-renewal`)
* attach policy `AmazonEC2ContainerRegistryFullAccess`

```bash
# required to create a repository and to upload images by the 
# user kacon-ch-certificate-renewal
$ aws iam attach-user-policy \
  --profile root \
  --user-name kacon-ch-certificate-renewal \
  --policy-arn arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryFullAccess

# required to list and create clusters with the user kacon-ch-certificate-renewal
$ aws iam attach-user-policy \
  --profile root \
  --user-name kacon-ch-certificate-renewal \
  --policy-arn arn:aws:iam::aws:policy/AmazonECS_FullAccess

$ aws iam attach-user-policy \
  --profile root \
  --user-name kacon-ch-certificate-renewal \
  --policy-arn arn:aws:iam::aws:policy/AWSKeyManagementServicePowerUser

$ aws iam attach-user-policy \
  --profile root \
  --user-name kacon-ch-certificate-renewal \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMFullAccess
```

Create a ECR repository. It will hold the all the versions of one images.
```bash
$ aws ecr create-repository \
  --profile root \
  --repository-name hello-world
```

Results in:
```json
{
    "repository": {
        "registryId": "154819770423", 
        "repositoryName": "hello-world", 
        "repositoryArn": "arn:aws:ecr:eu-central-1:154819770423:repository/hello-world", 
        "createdAt": 1537847970.0, 
        "repositoryUri": "154819770423.dkr.ecr.eu-central-1.amazonaws.com/hello-world"
    }
}
```

Tag the `hello-world` image with the Amazon ECR repository URI
```bash
$ sudo docker tag hello-world 154819770423.dkr.ecr.eu-central-1.amazonaws.com/hello-world
```

Let AWS prepare the docker login command:
```bash
$ aws ecr get-login \
  --profile root \
  --no-include-email
```
Results in:
```
docker login -u AWS -p eyJwYXlsb2FkI ... https://154819770423.dkr.ecr.eu-west-1.amazonaws.com
```

Invoke the command:
```bash
$ sudo docker login -u AWS -p eyJwYXlsb2FkI ... https://154819770423.dkr.ecr.eu-west-1.amazonaws.com
```

Push the image
```bash
$ sudo docker push 154819770423.dkr.ecr.eu-central-1.amazonaws.com/hello-world
```

List the available images the in the AWS ECR repository:
```bash
$ aws ecr list-images \
  --profile root \
  --repository-name hello-world
```

# Prequisites for AWS ECS

## a role `ecsTaskExecutionRole` must be configured

* with the following assigned policy: `AmazonECSTaskExecutionRolePolicy`

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": [
          "ec2.amazonaws.com",
          "ecs-tasks.amazonaws.com"
        ]
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
```


Möglicherweise auch diesen Service hinzufügen:`ssm.amazonaws.com`


```bash
# create the role 
$ aws iam create-role \
   --profile root \
   --role-name ecsTaskExecutionRole \
   --description "Allows EC2 instances to call AWS services on your behalf" \
   --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":["ec2.amazonaws.com","ecs-tasks.amazonaws.com"]},"Action":"sts:AssumeRole"}]}'

# attach it a policy
$ aws iam attach-role-policy \
  --profile root \
  --role-name ecsTaskExecutionRole \
  --policy-arn "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"
```

```bash
# create the role 
$ aws iam create-role \
   --profile root \
   --role-name helloWorldTaskExecution \
   --description "Allows hello-world tasks to call AWS services on our behalf" \
   --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":["ecs-tasks.amazonaws.com"]},"Action":"sts:AssumeRole"}]}'

$ aws iam attach-role-policy \
  --profile root \
  --role-name helloWorldTaskExecution \
  --policy-arn "arn:aws:iam::aws:policy/service-role/AmazonEC2ContainerServiceforEC2Role"

# attach it a policy
$ aws iam attach-role-policy \
  --profile root \
  --role-name helloWorldTaskExecution \
  --policy-arn "arn:aws:iam::154819770423:policy/AmazonSSMReadParameter"
```

## a default cluster must exists

```bash
$ aws ecs list-clusters \
  --profile root
```

If no default-cluster is listed, we have to create one.
```bash
$ aws ecs create-cluster \
  --profile root \
  --cluster default
```

# Create and run an AWS ECS task

The task is described in a __task definition__, see `hello-world-tasks.json`.

Register the task definition

* creates the task definition in the current zone. To change the zone, run `aws configure`

```bash
$ aws ecs register-task-definition \
  --profile root \
  --cli-input-json file://hello-world-task.json
```

Run a task, given a task definition

* `subnet` and `securityGroup` can be found on the ECS console, lookup the network panel

```bash
$ aws ecs run-task --task-definition hello-world-task:11 \
  --profile root \
  --launch-type FARGATE \
  --cluster default \
  --platform-version LATEST \
  --count 1 \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-29da8f64],securityGroups=[sg-c44921a8],assignPublicIp=ENABLED}"
```

# Send an email from the docker container

* use [mailgun](https://www.mailgun.com/)
* registered for free plan. See account in keypass
* log in, click on the only available domain, get API key

```bash
curl -s --user 'api:59af2a978bf107de19c9057eab3418cc-7efe8d73-1ba05e0a' \
    https://api.mailgun.net/v3/sandboxb5440a24d09e4617ab9286bcfe3d61d1.mailgun.org/messages \
    -F from=karl@sandboxb5440a24d09e4617ab9286bcfe3d61d1.mailgun.org \
    -F to=karl.guggisberg@kacon.ch \
    -F subject='hello-world' \
    -F text='hello-world'
```

# Manage secret parameters

```bash
# create the encryption key we use to encrypt secret parmeters 
$ aws kms create-key --description hello-world-key
```

```json
{
    "KeyMetadata": {
        "Origin": "AWS_KMS", 
        "KeyId": "53ecc9c2-365a-47d6-a657-5e2a2dd013b9", 
        "Description": "hello-world-key", 
        "KeyManager": "CUSTOMER", 
        "Enabled": true, 
        "KeyUsage": "ENCRYPT_DECRYPT", 
        "KeyState": "Enabled", 
        "CreationDate": 1534085712.127, 
        "Arn": "arn:aws:kms:eu-central-1:154819770423:key/53ecc9c2-365a-47d6-a657-5e2a2dd013b9", 
        "AWSAccountId": "154819770423"
    }
}
```

Encrypt and store a parameter

```bash
$ aws ssm put-parameter \
  --name mailgun.apikey \
  --value "<the mailgun api key>" \
  --type SecureString \
  --key-id "53ecc9c2-365a-47d6-a657-5e2a2dd013b9"


$ aws ssm put-parameter \
  --name hello-world.mailgun-api-key \
  --value "59af2a978bf107de19c9057eab3418cc-7efe8d73-1ba05e0a" \
  --type SecureString \
  --key-id "53ecc9c2-365a-47d6-a657-5e2a2dd013b9"


$ aws ssm put-parameter \
  --profile root \
  --name hello-world.message \
  --value "Message 1234" \
  --type String


$ aws ssm get-parameter \
  --profile root \
  --name hello-world.message 
```

```bash
$ aws ssm get-parameter \
  --name mailgun.apikey \
  --with-decryption

$ aws ssm get-parameter \
  --name hello-world.mailgun-api-key \
  --with-decryption
```

# Prepare IAM roles 

Need `iam:CreateRole` permission.

```bash
$ aws iam create-role \
    --role-name hello-world \
    --assume-role-policy-document file://ecs-tasks-trust-policy.json
```

Creates the following role
```json
{
    "Role": {
        "AssumeRolePolicyDocument": {
            "Version": "2012-10-17", 
            "Statement": [
                {
                    "Action": "sts:AssumeRole", 
                    "Principal": {
                        "Service": "ecs-tasks.amazonaws.com"
                    }, 
                    "Effect": "Allow", 
                    "Sid": ""
                }
            ]
        }, 
        "RoleId": "AROAJOVGWMTOOYZ7OGVEE", 
        "CreateDate": "2018-08-15T15:14:57Z", 
        "RoleName": "hello-world", 
        "Path": "/", 
        "Arn": "arn:aws:iam::154819770423:role/hello-world"
    }
}
```

```bash
$ aws iam create-policy \
  --policy-name hello-world-secret-access \
  --policy-document file://hello-world-secret-access.json
```

```json
{
    "Policy": {
        "PolicyName": "hello-world-secret-access", 
        "CreateDate": "2018-08-15T15:22:35Z", 
        "AttachmentCount": 0, 
        "IsAttachable": true, 
        "PolicyId": "ANPAIWUWNPRGC6XKELUXG", 
        "DefaultVersionId": "v1", 
        "Path": "/", 
        "Arn": "arn:aws:iam::154819770423:policy/hello-world-secret-access", 
        "UpdateDate": "2018-08-15T15:22:35Z"
    }
}
```

```bash
$ aws iam attach-role-policy \
  --role-name hello-world \
  --policy-arn "arn:aws:iam::154819770423:policy/hello-world-secret-access"
```


# Empty service image

```bash
$ sudo docker build -t empty-service-image -f empty-service-image.docker .
```

```bash
# create the ECS repository
$ aws ecr create-repository --repository-name empty-service-image
```

```json
{
    "repository": {
        "registryId": "154819770423", 
        "repositoryName": "empty-service-image", 
        "repositoryArn": "arn:aws:ecr:eu-central-1:154819770423:repository/empty-service-image", 
        "createdAt": 1534775300.0, 
        "repositoryUri": "154819770423.dkr.ecr.eu-central-1.amazonaws.com/empty-service-image"
    }
}
```

```bash
# tag the image
$ sudo docker tag empty-service-image 154819770423.dkr.ecr.eu-central-1.amazonaws.com/empty-service-image
```

```bash
# push the image
$ sudo docker push 154819770423.dkr.ecr.eu-central-1.amazonaws.com/empty-service-image
```

```bash
# register the task
$ aws ecs register-task-definition \
  --cli-input-json file://empty-service-task.json
```

# Log Groups

```bash
# create a log group
$ aws logs create-log-group \
    --profile root \
    --log-group-name hello-world

# describe log groups
$ aws logs describe-log-groups \
    --profile root

# delete log group
$ aws logs delete-log-group \
    --profile root \
    --log-group-name hello-world
```

# Amazon Cloudfront

```bash
$ aws cloudformation create-stack \
  --profile root \
  --stack-name test-iam-stack \
  --capabilities CAPABILITY_NAMED_IAM  \
  --template-body file://iam-template.yml


$ aws cloudformation describe-stacks \
  --profile root \
  --stack-name test-iam-stack

$ aws cloudformation delete-stack \
  --profile root \
  --stack-name test-iam-stack

$ aws cloudformation list-stack-resources \
  --profile root \
  --stack-name test-iam-stack



$ aws cloudformation create-stack \
  --profile root \
  --stack-name repository-stack \
  --template-body file://repository-template.yml

$ aws cloudformation delete-stack \
  --profile root \
  --stack-name repository-stack


$ aws cloudformation create-stack \
  --profile root \
  --capabilities CAPABILITY_NAMED_IAM  \
  --stack-name ecsTaskExecutionRole-stack \
  --template-body file://ecsTaskExecutionRole-role-template.yml

$ aws cloudformation delete-stack \
  --profile root \
  --stack-name ecsTaskExecutionRole-stack


$ aws cloudformation list-stack-resources \
  --profile root \
  --stack-name ecsTaskExecutionRole-stack


```

IAM Roles for Tasks - Notes
https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-iam-roles.html









