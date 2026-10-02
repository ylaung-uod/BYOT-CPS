PYTHON ?= python3
PROJECT_NAME ?= byot-cps
COMPROMISED_IOT_COUNT ?= 3
GNS3_SERVER_CONFIG ?= $(HOME)/.config/GNS3/2.2/gns3_server.conf
QEMU_PATH ?= /usr/bin/qemu-system-x86_64
IOT_INTERFACE ?= docker0
MGMT_INTERFACE ?= byot-mgmt
PFSENSE_CONFIG ?= config/pfsense-public.xml
PFSENSE_CONFIG_IMAGE ?= artifacts/pfsense-config.img
PFSENSE_INSTALLER_ARCHIVE ?= downloads/netgate-installer-v1.2-RELEASE-amd64.iso.gz
GNS3_QEMU_IMAGES ?= $(HOME)/GNS3/images/QEMU

.PHONY: validate fetch-help prepare-images verify-images docker-images container-sboms container-sboms-check container-runtime-test phase4-verify pfsense-config-validate pfsense-config-drive templates topology smoke-test reproduce

validate:
	$(PYTHON) src/validate.py

fetch-help:
	$(PYTHON) src/fetch_help.py

prepare-images:
	$(PYTHON) src/prepare_images.py --image-dir "$(GNS3_QEMU_IMAGES)" --archive "$(PFSENSE_INSTALLER_ARCHIVE)"

verify-images:
	$(PYTHON) src/verify_images.py --image-dir "$(GNS3_QEMU_IMAGES)"

docker-images:
	docker build --pull --tag byot-cps/ubuntu18-lab:latest Dockerfiles/ubuntu18-lab
	docker build --pull --tag byot-cps/ubuntu24-lab:latest Dockerfiles/ubuntu24-lab
	docker build --pull --tag byot-cps/ubuntu24-nginx:latest Dockerfiles/ubuntu24-nginx

container-sboms: docker-images
	$(PYTHON) src/generate_container_sboms.py

container-sboms-check: docker-images
	$(PYTHON) src/generate_container_sboms.py --check

container-runtime-test: docker-images
	$(PYTHON) src/test_container_images.py

phase4-verify: validate container-sboms-check container-runtime-test

pfsense-config-validate:
	$(PYTHON) src/pfsense_config.py "$(PFSENSE_CONFIG)"

pfsense-config-drive: pfsense-config-validate
	$(PYTHON) src/pfsense_config.py "$(PFSENSE_CONFIG)" --output "$(PFSENSE_CONFIG_IMAGE)"
	install -d "$(GNS3_QEMU_IMAGES)"
	install -m 600 "$(PFSENSE_CONFIG_IMAGE)" "$(GNS3_QEMU_IMAGES)/pfsense-config.img"

templates: validate prepare-images verify-images docker-images pfsense-config-drive
	GNS3_SERVER_CONFIG="$(GNS3_SERVER_CONFIG)" QEMU_PATH="$(QEMU_PATH)" $(PYTHON) src/create_templates.py

topology: validate
	GNS3_SERVER_CONFIG="$(GNS3_SERVER_CONFIG)" IOT_INTERFACE="$(IOT_INTERFACE)" MGMT_INTERFACE="$(MGMT_INTERFACE)" $(PYTHON) src/create_topology.py --project-name "$(PROJECT_NAME)" --compromised-iot-count "$(COMPROMISED_IOT_COUNT)"

smoke-test: validate
	GNS3_SERVER_CONFIG="$(GNS3_SERVER_CONFIG)" IOT_INTERFACE="$(IOT_INTERFACE)" MGMT_INTERFACE="$(MGMT_INTERFACE)" COMPROMISED_IOT_COUNT="$(COMPROMISED_IOT_COUNT)" $(PYTHON) src/smoke_test.py

reproduce: templates topology
