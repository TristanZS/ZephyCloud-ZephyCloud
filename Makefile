# Makefile for this project
# It's the main entry point for this project
# It provide the more common actions you want to do with
# a repository
# Run `make help` to list all the available actions

.DEFAULT_GOAL := list_targets
.PHONY: ami import_zt list_targets sync_dev sync_prod help

mkfile_path := $(abspath $(lastword $(MAKEFILE_LIST)))
project_path := $(dir  $(mkfile_path))

ami:
	@(cd "$(project_path)" && /usr/bin/env python tools/worker_utils/create_ami.py)

import_zt:
	@(cd "$(project_path)" && python tools/worker_utils/import_zephytools.py)

sync_dev:
	@(cd "$(project_path)" && export PYTHONPATH=; . venv/bin/activate; sh tools/sync_dev.sh)

sync_prod:
	@(cd "$(project_path)" && export PYTHONPATH=; . venv/bin/activate; sh tools/sync_prod.sh)

help: list_targets ;

list_targets:
	@echo "Usage: make TARGET1 [TARGET2 ...]"
	@echo ""
	@echo "List of make targets:"
	@echo "  help:            Show this help message"
	@echo "  ami:             Create a worker AMI quicly, without updating dependencies"
	@echo "  import_zt:       Import ZephyTools source code for the AMI"
	@echo "  sync_dev:        Deploy source code on dev server"
	@echo "  sync_prod:       Deploy source code on production server"
	@echo ""
