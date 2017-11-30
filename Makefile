.PHONY: test
test:
	tox -etest

.PHONY: lint
lint:
	tox -elint

