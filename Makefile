BLENDER ?= /Applications/Blender.app/Contents/MacOS/Blender
UV ?= uv
LINT_PATHS ?= .

.PHONY: sync test test-blender build install lint format
sync:
	$(UV) sync --locked
test:
	$(UV) run --locked --no-env-file python -m pytest
lint:
	$(UV) run --locked ruff check -- $(LINT_PATHS)
	$(UV) run --locked ruff format --check -- $(LINT_PATHS)
format:
	@result=0; \
	$(UV) run --locked ruff check --fix -- $(LINT_PATHS) || result=$$?; \
	$(UV) run --locked ruff format -- $(LINT_PATHS) || exit $$?; \
	exit $$result
test-blender:
	$(BLENDER) --background --python-exit-code 1 --python tests/blender/run_all.py
build:
	./tools/build.sh
install:
	./tools/install_dev.sh
