# No dependencies to install. Python 3.10+ and git are the whole toolchain.
.POSIX:
.PHONY: build live check test audit preview clean help

PYTHON ?= python3

help:
	@echo "build    render from the committed snapshot (no network)"
	@echo "live     fetch fresh data from the GitHub API, then render"
	@echo "test     run the test suite"
	@echo "check    assert committed output matches a fresh render"
	@echo "audit    scan generated output for secrets and active content"
	@echo "preview  build, then show what changed"

build:
	@$(PYTHON) -m generator --offline

live:
	@$(PYTHON) -m generator

check:
	@$(PYTHON) -m generator --check

test:
	@$(PYTHON) -m unittest discover -s tests

audit:
	@$(PYTHON) tools/audit_output.py --strict

preview: build audit
	@git --no-pager diff --stat -- README.md assets data 2>/dev/null || true

clean:
	@rm -f assets/*.svg.tmp README.md.tmp
