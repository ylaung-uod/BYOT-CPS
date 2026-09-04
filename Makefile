PYTHON ?= python3
SOURCE_PROJECT ?= Firewall_Test_HMS/Firewall_Test_HMS.gns3
PROJECT_NAME ?= byot-cps
COMPROMISED_IOT_COUNT ?= 3
GNS3_SERVER_CONFIG ?= $(HOME)/.config/GNS3/2.2/gns3_server.conf
QEMU_PATH ?= /usr/bin/qemu-system-x86_64
IOT_INTERFACE ?= docker0
PFSENSE_CONFIG ?= config/pfsense-public.xml
PFSENSE_CONFIG_IMAGE ?= artifacts/pfsense-config.img
PFSENSE_INSTALLER_ARCHIVE ?= downloads/netgate-installer-v1.2-RELEASE-amd64.iso.gz
GNS3_QEMU_IMAGES ?= $(HOME)/GNS3/images/QEMU
HADOLINT_IMAGE ?= hadolint/hadolint:v2.12.0-debian@sha256:27173fe25e062448490a32de410c08491c626a0bef360aa2ce5d5bdd9384b50d
GITLEAKS_IMAGE ?= zricethezav/gitleaks:v8.28.0@sha256:cdbb7c955abce02001a9f6c9f602fb195b7fadc1e812065883f695d1eeaba854
RUFF_IMAGE ?= ghcr.io/astral-sh/ruff:0.12.11@sha256:1c569ad1fd700da41578080d68237f1e72e98b42e0d77b7179958427e1461eb1
ACTIONLINT_IMAGE ?= rhysd/actionlint:1.7.7@sha256:887a259a5a534f3c4f36cb02dca341673c6089431057242cdc931e9f133147e9
LYCHEE_IMAGE ?= lycheeverse/lychee:0.24.2@sha256:e2d19e57cf6ab037026f20b8e449a1f30d9d7f81eef4194763aab2eab20bd28d
SELF_RELEASE_URL ?= ^https://github[.]com/ylaung-uod/byot-cps/releases/tag/v1[.]0[.]0$$
REPRODUCTION_ARCHIVE ?= dist/byot-cps-v1.0.0-reproduction.tar.gz

.PHONY: test validate validate-data whitespace-check markdown-link-check external-link-check python-static workflow-lint secret-scan dockerfile-lint archive-inspect reproduction-archive ci-static container-ci release-check live-release-check fetch-help prepare-images verify-images docker-images container-sboms container-sboms-check container-runtime-test phase4-verify pfsense-config-validate pfsense-config-drive templates topology smoke-test refresh-spec

test:
	$(PYTHON) -m unittest discover -s tests -v

validate:
	$(PYTHON) src/validate.py

validate-data:
	$(PYTHON) src/quality_gates.py data

whitespace-check:
	git diff --check
	git diff --cached --check

markdown-link-check:
	$(PYTHON) src/quality_gates.py markdown

external-link-check:
	docker run --rm -v "$(CURDIR):/input:ro" -w /input $(LYCHEE_IMAGE) --no-progress --exclude '$(SELF_RELEASE_URL)' './**/*.md'

python-static:
	$(PYTHON) src/quality_gates.py python
	docker run --rm -v "$(CURDIR):/repo:ro" -w /repo $(RUFF_IMAGE) check --no-cache .

workflow-lint:
	docker run --rm -v "$(CURDIR):/repo:ro" -w /repo $(ACTIONLINT_IMAGE) -color

secret-scan:
	@set -eu; tmp=$$(mktemp -d); trap 'rm -rf "$$tmp"' EXIT; \
	  git archive --format=tar "$$(git write-tree)" | tar -x -C "$$tmp"; \
	  docker run --rm -v "$$tmp:/repo:ro" $(GITLEAKS_IMAGE) detect --source=/repo --no-git --redact --config=/repo/.gitleaks.toml --exit-code=1

dockerfile-lint:
	docker run --rm -v "$(CURDIR):/repo:ro" $(HADOLINT_IMAGE) hadolint --config /repo/.hadolint.yaml --ignore SC2016 /repo/Dockerfiles/ubuntu18-lab/Dockerfile /repo/Dockerfiles/ubuntu24-lab/Dockerfile

archive-inspect:
	@git archive --format=tar "$$(git write-tree)" | $(PYTHON) src/inspect_archive.py -

reproduction-archive:
	$(PYTHON) src/build_reproduction_archive.py --output "$(REPRODUCTION_ARCHIVE)"

ci-static: validate validate-data test markdown-link-check external-link-check python-static workflow-lint secret-scan dockerfile-lint archive-inspect

container-ci: container-sboms-check container-runtime-test

release-check:
	@set -eu; trap 'status=$$?; echo "RELEASE CHECK: FAILED (exit $$status)"' EXIT; \
	  test -z "$$(git diff --name-only)" || { echo "unstaged tracked changes must be staged" >&2; exit 1; }; \
	  test -z "$$(git ls-files --others --exclude-standard)" || { echo "untracked files must be staged or ignored" >&2; exit 1; }; \
	  $(MAKE) validate validate-data test whitespace-check markdown-link-check external-link-check python-static workflow-lint secret-scan dockerfile-lint archive-inspect reproduction-archive container-sboms-check container-runtime-test; \
	  trap - EXIT; echo "RELEASE CHECK: PASSED"

live-release-check: templates
	GNS3_SERVER_CONFIG="$(GNS3_SERVER_CONFIG)" IOT_INTERFACE="$(IOT_INTERFACE)" $(PYTHON) src/live_release_check.py

fetch-help:
	$(PYTHON) src/fetch_help.py

prepare-images:
	$(PYTHON) src/prepare_images.py --image-dir "$(GNS3_QEMU_IMAGES)" --archive "$(PFSENSE_INSTALLER_ARCHIVE)"

verify-images:
	$(PYTHON) src/verify_images.py --image-dir "$(GNS3_QEMU_IMAGES)"

docker-images:
	docker build --pull --tag byot-cps/ubuntu18-lab:latest Dockerfiles/ubuntu18-lab
	docker build --pull --tag byot-cps/ubuntu24-lab:latest Dockerfiles/ubuntu24-lab

container-sboms: docker-images
	$(PYTHON) src/generate_container_sboms.py

container-sboms-check: docker-images
	$(PYTHON) src/generate_container_sboms.py --check

container-runtime-test: docker-images
	$(PYTHON) src/test_container_images.py

phase4-verify: test container-sboms-check container-runtime-test

pfsense-config-validate:
	$(PYTHON) src/pfsense_config.py "$(PFSENSE_CONFIG)"

pfsense-config-drive: pfsense-config-validate
	$(PYTHON) src/pfsense_config.py "$(PFSENSE_CONFIG)" --output "$(PFSENSE_CONFIG_IMAGE)"
	install -d "$(GNS3_QEMU_IMAGES)"
	install -m 600 "$(PFSENSE_CONFIG_IMAGE)" "$(GNS3_QEMU_IMAGES)/pfsense-config.img"

templates: validate prepare-images verify-images docker-images pfsense-config-drive
	GNS3_SERVER_CONFIG="$(GNS3_SERVER_CONFIG)" QEMU_PATH="$(QEMU_PATH)" $(PYTHON) src/create_templates.py

topology: validate
	GNS3_SERVER_CONFIG="$(GNS3_SERVER_CONFIG)" IOT_INTERFACE="$(IOT_INTERFACE)" $(PYTHON) src/create_topology.py --project-name "$(PROJECT_NAME)" --compromised-iot-count "$(COMPROMISED_IOT_COUNT)"

smoke-test: validate
	GNS3_SERVER_CONFIG="$(GNS3_SERVER_CONFIG)" IOT_INTERFACE="$(IOT_INTERFACE)" COMPROMISED_IOT_COUNT="$(COMPROMISED_IOT_COUNT)" $(PYTHON) src/smoke_test.py

refresh-spec:
	$(PYTHON) src/export_project.py "$(SOURCE_PROJECT)" topology.json
