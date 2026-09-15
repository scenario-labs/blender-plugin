BLENDER ?= /Applications/Blender.app/Contents/MacOS/Blender
PYTHON ?= python3
LINT_PATHS ?= .

.PHONY: test test-blender build install lint format
test:
	$(PYTHON) -m pytest
lint:
	$(PYTHON) -m ruff check $(LINT_PATHS)
	$(PYTHON) -m ruff format --check $(LINT_PATHS)
format:
	@result=0; \
	$(PYTHON) -m ruff check --fix $(LINT_PATHS) || result=$$?; \
	$(PYTHON) -m ruff format $(LINT_PATHS) || exit $$?; \
	exit $$result
test-blender:
	$(BLENDER) --background --python-exit-code 1 --python tests/blender/run_all.py
build:
	./tools/build.sh
install:
	./tools/install_dev.sh
