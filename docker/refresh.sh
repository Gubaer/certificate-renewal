#!/bin/bash

IMAGE_ID=$(sudo docker images | grep 154819770423.dkr.ecr.eu-central-1.amazonaws.com/hello-world | awk '{print($3)}'
8fa2af84d563)
sudo docker rmi -f $IMAGE_ID
sudo docker build -t hello-world -f hello-world.docker .
sudo docker tag hello-world 154819770423.dkr.ecr.eu-central-1.amazonaws.com/hello-world
sudo docker push 154819770423.dkr.ecr.eu-central-1.amazonaws.com/hello-world


