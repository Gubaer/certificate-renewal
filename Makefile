build-container:
	docker build \
		-t certificate-renewal \
		-f docker/Dockerfile.alpine \
		.

delete-container:
	-docker rmi -f certificate-renewal