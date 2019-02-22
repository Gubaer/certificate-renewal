ROOT_DIR:=$(shell dirname $(realpath $(lastword $(MAKEFILE_LIST))))
SHELL := /bin/bash
FUNCTION_NAME = "certificate-renewal"
DEPLOYMENT_PACKGE = "certificate-renewal.zip"
SUBNET=subnet-29da8f64
SECURITY_GROUP=sg-c44921a8

zip:
	rm certificate-renewal.zip
	zip certificate-renewal.zip function.py
	# no need to include boto3 in the deployment package. boto3 is 
	# provided by the AWS lambda runtime
	#cd env/lib/python3.6/site-packages \
	#	&& zip -r9 ${ROOT_DIR}/certificate-renewal.zip *

create: zip
	aws lambda create-function \
		--function-name ${FUNCTION_NAME} \
		--runtime "python3.6" \
		--handler function.handler \
		--role "arn:aws:iam::154819770423:role/certificateRenewalExecutionRole" \
		--zip-file fileb://${DEPLOYMENT_PACKGE} \
		--environment Variables="{\
			SUBNET=${SUBNET}, \
			SECURITY_GROUP=${SECURITY_GROUP}, \
			TASK_FAMILY_PREFIX=${FUNCTION_NAME} \
		}"

remove:
	aws lambda delete-function \
		--function-name ${FUNCTION_NAME}

upload: zip
	aws lambda update-function-code \
		--function-name ${FUNCTION_NAME} \
		--zip-file fileb://${DEPLOYMENT_PACKGE}

init-env:
	@if [ -d "env" ]; then \
		echo "INFO: virtualenv already exists" ; \
		exit 0 ;\
	else \
		virtualenv -p python3 env; \
		source env/bin/activate; \
		pip3 install boto3; \
	fi


invoke:
	aws lambda invoke \
		--function-name ${FUNCTION_NAME} \
		${FUNCTION_NAME}.out




