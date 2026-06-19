-include .env

APP     := tater
VERSION := $(shell grep '^version' pyproject.toml | awk -F'"' '{print $$2}')
IMAGE   := $(REGISTRY)/$(APP):$(VERSION)

.PHONY: help build run stop push release pod-up pod-down pod-bounce pod-logs pod-logs-follow \
        az-login az-deploy az-logs az-logs-follow

help:
	@echo "build               Build the Docker image"
	@echo "run                 Run the container locally on :8050"
	@echo "stop                Stop the running container"
	@echo "push                Push the image to the registry"
	@echo "release             Build and push (build + push)"
	@echo "pod-up              Deploy to Kubernetes via Helm (K8S_NAMESPACE=$(K8S_NAMESPACE))"
	@echo "pod-down            Uninstall Helm release"
	@echo "pod-bounce          Uninstall then reinstall Helm release"
	@echo "pod-logs            Print pod logs"
	@echo "pod-logs-follow     Stream pod logs"
	@echo "az-login            Log in to Azure"
	@echo "az-deploy           Update Container App image to current VERSION"
	@echo "az-logs             Print Container App logs"
	@echo "az-logs-follow      Stream Container App logs"

# Docker

build:
	docker build -t $(IMAGE) .

run:
	docker run --rm --name $(APP) -p 8050:8050 $(IMAGE)

stop:
	docker stop $(APP)

push:
	docker push $(IMAGE)

release: build push

# Azure Container Apps

az-login:
	az login

az-deploy:
	az containerapp update \
		--name $(AZ_APP_NAME) \
		--resource-group $(AZ_RESOURCE_GROUP) \
		--image $(IMAGE)

az-logs:
	az containerapp logs show \
		--name $(AZ_APP_NAME) \
		--resource-group $(AZ_RESOURCE_GROUP) \
		--tail 50

az-logs-follow:
	az containerapp logs show \
		--name $(AZ_APP_NAME) \
		--resource-group $(AZ_RESOURCE_GROUP) \
		--follow

# Kubernetes / Helm

pod-up:
	helm upgrade --install $(APP) ./k8s/chart -n $(K8S_NAMESPACE) \
		--set appVersion=$(VERSION)

pod-down:
	helm uninstall $(APP) -n $(K8S_NAMESPACE)

pod-bounce: pod-down pod-up

pod-logs:
	kubectl logs -n $(K8S_NAMESPACE) deploy/$(APP)

pod-logs-follow:
	kubectl logs -n $(K8S_NAMESPACE) deploy/$(APP) -f
