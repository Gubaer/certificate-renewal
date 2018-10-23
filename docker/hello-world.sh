#!/bin/bash

MESSAGE=$(aws ssm get-parameter --name hello-world.message)
echo "Message: $MESSAGE"
