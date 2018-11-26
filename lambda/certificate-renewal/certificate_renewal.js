/*
* AWS lambda function to launch an Amazon ECS task
*/
const AWS = require('aws-sdk');
const ECS = new AWS.ECS({apiVersion: '2014-11-13'});

// the prefix of the ECS task family
const familyPrefix = "certificate-renewal";

/**
* looks up the ARN of the most recent task definition (the definition with the
* highest version number) for with the family prefix $familyPrefix
*/
async function getTaskDefinitionArn() {
    const params = {
        familyPrefix: familyPrefix
    };
    return ECS.listTaskDefinitions(params).promise()
        .then(data => {
            let len = data.taskDefinitionArns.length;
            if (len == 0) {
                throw new Error(
                    `Didn't find a task definition for task family `
                  + `'${familyPrefix}'`);
            } else {
                let taskDefinitionArn = data.taskDefinitionArns[len - 1];
                console.log(`Using task definition ARN '${taskDefinitionArn}'`);
                return taskDefinitionArn;
            }
        });
}

exports.handler = async function(event, context) {
    let subnet = process.env.SUBNET;
    let securityGroup = process.env.SECURITY_GROUP;
    let clusterName = "default";
    if (!subnet) {
        const msg = `FATAL: missing environment variable SUBNET`;
        console.log(msg);
        throw new Error(msg);
    }
    if (!securityGroup) {
        const msg = `FATAL: missing environment variable SECURITY_GROUP`;
        console.log(msg);
        throw new Error(msg);
    }
    
    return getTaskDefinitionArn()
    .then(taskArn => {
        const params = {
            cluster: clusterName,
            launchType: "FARGATE",
            networkConfiguration: {
                awsvpcConfiguration: {
                    subnets: [subnet],
                    securityGroups: [securityGroup],
                    assignPublicIp: "ENABLED"
                }
            },
            taskDefinition: taskArn,
            count: 1
        };
        ECS.runTask(params).promise()
        .then(data => {
            console.info(
                `Task ${taskArn} started: `
              + `${JSON.stringify(data.tasks)}`);
        });
    })
    .catch(err => {
        console.warn('error: ', `Error while starting task: ${err}`);
    });
}