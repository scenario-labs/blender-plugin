ifdef BLENDER
export BLENDER
endif
BLENDER_BUILD_ARGS ?=
BLENDER_INSTALL_ARGS ?=
BLENDER_TEST_ARGS ?=
BLENDER_GUI_ARGS ?=
LANE ?= image
UV ?= uv
LINT_PATHS ?= .

.PHONY: sync test test-blender build repo install install-isolated gui-check lint format knowledge mcp-docs check-rules docs hooks
check-rules:
	$(UV) run --locked --no-env-file python tools/check_rules.py
knowledge:
	$(UV) run --locked --no-env-file python tools/check_knowledge.py
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
repo:
	$(UV) run --locked --no-env-file python tools/build.py --repo $(BLENDER_BUILD_ARGS)
install install-isolated:
	$(UV) run --locked --no-env-file python tools/install.py $(BLENDER_INSTALL_ARGS)
gui-check:
	$(UV) run --locked --no-env-file python tools/capture_gui.py --lane "$(LANE)" $(BLENDER_GUI_ARGS)

mcp-docs:
	$(UV) run --locked --no-env-file python tools/gen_mcp_docs.py --write

docs:
	$(UV) run --locked --no-env-file python tools/build_docs_html.py

hooks:
	$(UV) run --locked --no-env-file pre-commit install --hook-type pre-commit --hook-type commit-msg
