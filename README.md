
# Prepare and upload a simple docker images

```bash
# create the docker image
$ docker build -t hello-world -f hello-world.docker .
```

To access the Amazon ECR services
* create an IAM user (in my case: `kacon-ch-certificate-renewal`)
* attach policy `AmazonEC2ContainerRegistryFullAccess`


Create a ECR repository. It will hold the all the versions of one images.
```bash
$ aws ecr create-repository --repository-name hello-world
```

Results in:
```json
{
    "repositories": [
        {
            "registryId": "154819770423",
            "repositoryName": "hello-world",
            "repositoryArn": "arn:aws:ecr:eu-west-1:154819770423:repository/hello-world",
            "createdAt": 1534063409.0,
            "repositoryUri": "154819770423.dkr.ecr.eu-west-1.amazonaws.com/hello-world"
        }
    ]
}
```

Tag the `hello-world` image with the Amazon ECR repository URI
```bash
$ docker tag hello-world 154819770423.dkr.ecr.eu-west-1.amazonaws.com/hello-world
```

Let AWS prepare the docker login command:
```bash
$ aws ecr get-login --no-include-email
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
$ aws ecr list-images --repository-name hello-world
```

# Prequisites for AWS ECS

## a role `ecsTaskExecutionRole` must be configured

* with the following assigned policy: `AmazonECSTaskExecutionRolePolicy`

## a default cluster must exists

```bash
$ aws ecs list-clusters
```

If no default-cluster is listed, we have to create one.
```bash
$ aws ecs create-cluster --cluster default
```

# Create and run an AWS ECS task

The task is described in a __task definition__, see `hello-world-tasks.json`.

Register the task definition

* creates the task definition in the current zone. To change the zone, run `aws configure`

```bash
$ aws ecs register-task-definition --cli-input-json file://hello-world-tasks.json
```

Run a task, given a task definition

* `subnet` and `securityGroup` can be found on the ECS console, lookup the network panel

```bash
$ aws ecs run-task --task-definition hello-world-task:2 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[subnet-29da8f64],securityGroups=[sg-c44921a8]}"
```


