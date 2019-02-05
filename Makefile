build-container:
	docker build \
		-t certificate-renewal \
		-f docker/Dockerfile \
		.