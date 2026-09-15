ifdef BLENDER
export BLENDER
endif
BLENDER_BUILD_ARGS ?=
BLENDER_INSTALL_ARGS ?=
BLENDER_TEST_ARGS ?=
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
	$(UV) run --locked --no-env-file python tools/test_blender.py $(BLENDER_TEST_ARGS)
build:
	$(UV) run --locked --no-env-file python tools/build.py $(BLENDER_BUILD_ARGS)
install:
	$(UV) run --locked --no-env-file python tools/install.py $(BLENDER_INSTALL_ARGS)
