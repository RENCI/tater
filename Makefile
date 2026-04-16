REGISTRY := containers.renci.org/clin-ann
APP      := tater
VERSION  := $(shell grep '^appVersion:' k8s/chart/Chart.yaml | awk -F'"' '{print $$2}')
IMAGE    := $(REGISTRY)/$(APP):$(VERSION)

NAMESPACE ?= clin-ann

.PHONY: build run stop push release deploy

build:
	docker build -t $(IMAGE) .

run:
	docker run --rm --name $(APP) -p 8050:8050 $(IMAGE)

stop:
	docker stop $(APP)

push:
	docker push $(IMAGE)

release: build push

deploy:
	helm upgrade --install $(APP) ./k8s/chart -n $(NAMESPACE)
