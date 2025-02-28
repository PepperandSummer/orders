# These can be overidden with env vars.
REGISTRY ?= us.icr.io
NAMESPACE ?= nicksome
IMAGE_NAME ?= orders
IMAGE_TAG ?= 1.2
IMAGE ?= $(REGISTRY)/$(NAMESPACE)/$(IMAGE_NAME):$(IMAGE_TAG)
# PLATFORM ?= "linux/amd64,linux/arm64"
PLATFORM ?= "linux/amd64"
CLUSTER ?= nyu-devops
SPACE ?= dev

.PHONY: help
help: ## Display this help.
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

.PHONY: all
all: help

##@ Development

.PHONY: clean
clean:	## Removes all dangling build cache
	$(info Removing all dangling build cache..)
	-docker rmi $(IMAGE)
	docker image prune -f
	docker buildx prune -f

.PHONY: venv
venv: ## Create a Python virtual environment
	$(info Creating Python 3 virtual environment...)
	python3 -m venv .venv

.PHONY: install
install: ## Install dependencies
	$(info Installing dependencies...)
	sudo pip install -r requirements.txt

.PHONY: lint
lint: ## Run the linter
	$(info Running linting...)
	 # stop the build if there are Python syntax errors or undefined names
	flake8 . --count --select=E9,F63,F7,F82 --show-source --statistics
	# exit-zero treats all errors as warnings. The GitHub editor is 127 chars wide
	flake8 . --count --max-complexity=10 --max-line-length=127 --statistics
	# Run pylint on the service
	pylint service

.PHONY: test
test: ## Run the unit tests
	$(info Running tests...)
	nosetests --with-spec --spec-color

.PHONY: run
run: ## Run the service
	$(info Starting service...)
	honcho start

.PHONY: namespace
namespace: ## Create the namespace assigned to the SPACE env variable
	$(info Creatng the $(SPACE) namespace...)
	kubectl create namespace $(SPACE) 
	kubectl get secret all-icr-io -n default -o yaml | sed 's/default/$(SPACE)/g' | kubectl create -n $(SPACE) -f -
	kubectl config set-context --current --namespace $(SPACE)

############################################################
# COMMANDS FOR DEPLOYING THE IMAGE
############################################################

##@ Deployment

.PHONY: login
login: ## Login to IBM Cloud using yur api key
	$(info Logging into IBM Cloud cluster $(CLUSTER)...)
	ibmcloud login -a cloud.ibm.com -g Default -r us-south --apikey @~/.bluemix/apikey-proj.json
	ibmcloud cr login
	ibmcloud ks cluster config --cluster $(CLUSTER)
	kubectl cluster-info

.PHONY: push
image-push: ## Push to a Docker image registry
	$(info Logging into IBM Cloud cluster $(CLUSTER)...)
	ibmcloud cr login
	docker push $(IMAGE)

.PHONY: deploy
deploy: ## Deploy the service on local Kubernetes
	$(info Deploying service locally...)
	kubectl apply -f deploy/

############################################################
# COMMANDS FOR BUILDING THE IMAGE
############################################################

##@ Docker Build

.PHONY: init
init: export DOCKER_BUILDKIT=1
init:	## Creates the buildx instance
	$(info Initializing Builder...)
	docker buildx create --use --name=qemu
	docker buildx inspect --bootstrap

.PHONY: build
build:	## Build all of the project Docker images
	$(info Building $(IMAGE) for $(PLATFORM)...)
	docker buildx build --file Dockerfile  --pull --platform=$(PLATFORM) --tag $(IMAGE) --load .

.PHONY: remove
remove:	## Stop and remove the buildx builder
	$(info Stopping and removing the builder image...)
	docker buildx stop
	docker buildx rm

.PHONY: tag
image-tag:
	$(info $(IMAGE_TAG))