#
# lambda function to run the certificate renewal ECS task
#
import boto3
import os
import logging

# default task family prefix. Override with the environment variable
# TASK_FAMILY_PREFIX
DEFAULT_TASK_FAMILY_PREFIX="certificate-renewal"

logger = logging.getLogger()
logger.setLevel(logging.INFO)

subnet = os.getenv("SUBNET")
securityGroup = os.getenv("SECURITY_GROUP")
taskFamilyPrefix = os.getenv("TASK_FAMILY_PREFIX")
if taskFamilyPrefix == None:
    logger.warning(
        ("environment variable TASK_FAMILY_PREFIX not set. " +
        "Using default task family prefix '{0}'.").format(
            DEFAULT_TASK_FAMILY_PREFIX
        ))
    taskFamilyPrefix = DEFAULT_TASK_FAMILY_PREFIX

class MissingEnvironmentException(Exception):
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return "MissingEnvironmentException: {0}".format(self.message)

def ensure_environment():
    if subnet == None:
        msg = "environment variable 'SUBNET' not set"
        raise MissingEnvironmentException(msg)
    if securityGroup == None:
        msg = "environment variable 'SECURITY_GROUP' not set"
        raise MissingEnvironmentException(msg)

def task_definition_arn(ecs_client, prefix=taskFamilyPrefix):
    """Looks up the the task definition ARN for the most recent task
    definition in the family prefix"""
    response = ecs_client.list_task_definitions(
        familyPrefix=prefix,
        sort="DESC"
    )
    if len(response["taskDefinitionArns"]) == 0:
        logger.warning(
            "no task definitions ARNs found for family '{0}'".format(
                prefix)
        )
        return None
    else:
        # ignore pagination. We are only interested in the most recent
        # task definition arn 
        arn = response["taskDefinitionArns"][0]
        logger.info("found most recent task definotion arn " +
            "for task family '{0}': '{1}'".format(
                prefix, arn
            ))
        return arn

def run_task(ecs_client, taskDefinitionArn):
    response = ecs_client.run_task(
        cluster="default",
        launchType="FARGATE",
        taskDefinition=taskDefinitionArn,
        count=1,
        platformVersion="LATEST",
        networkConfiguration = {
            "awsvpcConfiguration": {
                "subnets": [subnet],
                "securityGroups": [securityGroup],
                "assignPublicIp": "ENABLED"
            }
        }
    )
    logger.info(response)

def handler(event, context):
    """handler for lambda function"""
    logger.info("Starting")
    try:
        ensure_environment()
    except MissingEnvironmentException as e:
        logger.error(e.message)
        raise e
    ecs_client = boto3.client("ecs")
    taskDefinitionArn = task_definition_arn(ecs_client)
    run_task(ecs_client, taskDefinitionArn)

