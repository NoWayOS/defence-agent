# Defence Agent: `make` (or `make help`) lists the targets.
#
# Every target runs in NoWayOS's dev container, through the helper in a
# nowayos clone beside this one (nowayos/tools/make/container.mk): build the
# image once with `make container` in nowayos. Each run has no network and
# mounts the folder holding the clones read-only: what Defence Agent reads
# may be hostile, so it can neither write there nor send anything out.
#
# make gates-check reads the open repositories' Makefiles from clones beside
# this one: ../nowayos, ../screen-compiler and ../showcase. make check-patch
# reads a pull request's patch as text, and ../nowayos for its pins.

PYTHON ?= python3
GATES_REPOS := nowayos=../nowayos screen-compiler=../screen-compiler showcase=../showcase defence-agent=.

-include ../nowayos/tools/make/container.mk

.DEFAULT_GOAL := help
.PHONY: help secrets test gates-check check-patch ci ci-local

help:
	@echo "Defence Agent make targets (in NoWayOS's dev container, offline, read-only)"
	@echo "  make secrets      scan the tree and every commit for keys and credentials"
	@echo "  make test         the tools' own tests"
	@echo "  make gates-check  every open repository's make ci steps are in GATES.md (gate B22)"
	@echo "  make check-patch REPO=NAME PATCH=FILE"
	@echo "                    a pull request's patch, read as text (gates P1 to P10): FILE is"
	@echo "                    git format-patch --stdout BASE..HEAD, inside the workspace, relative to here"
	@echo "  make ci           secrets, test, gates-check"

ci-local: secrets test gates-check

ifeq ($(NOWAYOS_CONTAINER),1)
# Inside the dev container: run the checks directly, writing no bytecode.
export PYTHONDONTWRITEBYTECODE := 1

secrets:
	$(PYTHON) ../nowayos/tools/secrets-scan --repo . --allow secrets-allow.toml

test:
	$(PYTHON) -m unittest discover -s tools -p 'test_*.py'

gates-check:
	$(PYTHON) tools/check-gates --gates GATES.md $(GATES_REPOS)

check-patch:
	@test -n "$(REPO)" && test -n "$(PATCH)" || { echo "error: name both: make check-patch REPO=NAME PATCH=FILE" >&2; exit 2; }
	$(PYTHON) tools/check-patch --owners OWNERS.md --repo $(REPO) --nowayos ../nowayos $(PATCH)

ci: ci-local
else ifdef IN_CONTAINER
# On the host: every run in the dev container, offline and read-only.
CONTAINER_RUN_ARGS += --network=none
CONTAINER_BIND_OPTS := :ro
secrets test gates-check:
	$(IN_CONTAINER) make $@
check-patch:
	$(IN_CONTAINER) make $@ REPO=$(REPO) PATCH=$(PATCH)
ci:
	$(IN_CONTAINER) make ci-local
else
secrets test gates-check check-patch ci:
	@echo "error: make $@ needs ../nowayos/tools/make/container.mk - clone nowayos beside defence-agent" >&2
	@exit 1
endif
