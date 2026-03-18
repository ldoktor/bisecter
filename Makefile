ifndef PYTHON
PYTHON=$(shell which python3 2>/dev/null || which python 2>/dev/null)
endif

all:
	@echo
	@echo "Development related targets:"
	@echo "check:    Executes selftests"
	@echo "coverage: Runs selftests with coverage report"
	@echo "develop:  Installs package in editable mode"
	@echo "clean:    Get rid of scratch and byte files"
	@echo "docs:     Build html docs in docs/build/html/ dir"
	@echo
	@echo "Platform independent distribution/installation related targets:"
	@echo "build:    Build package"
	@echo "pypi:     Prepare package for pypi upload"
	@echo "install:  Install on local system"

check: develop
	@echo "RUNNING SELFTESTS:";
	$(PYTHON) ./selftests/run
	@echo RUNNING DOCUMENTATION CHECK:
	make -C docs html SPHINXOPTS="-W --keep-going -n"

coverage: develop
	./selftests/run_coverage

develop:
	$(PYTHON) -m pip install -e ".[dev]"

clean:
	rm -rf build/ MANIFEST BUILD BUILDROOT SPECS RPMS SRPMS SOURCES dist/ docs/build/
	rm -rf *.egg-info
	find . -name '*.pyc' -delete
	find . -name '__pycache__' -type d -delete

docs: develop
	make -C docs html

build: clean
	$(PYTHON) -m build

pypi: build
	@echo
	@echo "Use 'python3 -m twine upload dist/*'"
	@echo "to upload this release"

install:
	$(PYTHON) -m pip install .

.PHONY: check coverage develop clean build pypi install docs
