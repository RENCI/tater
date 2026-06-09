REGISTRY := containers.renci.org/clin-ann
APP      := tater
VERSION  := $(shell grep '^appVersion:' k8s/chart/Chart.yaml | awk -F'"' '{print $$2}')
IMAGE    := $(REGISTRY)/$(APP):$(VERSION)

NAMESPACE ?= clin-ann

.PHONY: help build run stop push release pod-up pod-down pod-bounce pod-logs pod-logs-follow

help:
	@echo "build             Build the Docker image"
	@echo "run               Run the container locally on :8050"
	@echo "stop              Stop the running container"
	@echo "push              Push the image to the registry"
	@echo "release           Build and push (build + push)"
	@echo "pod-up            Deploy to Kubernetes via Helm (NAMESPACE=$(NAMESPACE))"
	@echo "pod-down          Uninstall Helm release"
	@echo "pod-bounce        Uninstall then reinstall Helm release"
	@echo "pod-logs          Print pod logs"
	@echo "pod-logs-follow   Stream pod logs"

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

# Kubernetes / Helm

pod-up:
	helm upgrade --install $(APP) ./k8s/chart -n $(NAMESPACE)

pod-down:
	helm uninstall $(APP) -n $(NAMESPACE)

pod-bounce: pod-down pod-up

pod-logs:
	kubectl logs -n $(NAMESPACE) deploy/$(APP)

pod-logs-follow:
	kubectl logs -n $(NAMESPACE) deploy/$(APP) -f
