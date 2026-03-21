CONFIG ?= config.yaml

.PHONY: dev test screenshot lookup

dev:
	python -m src.main --config $(CONFIG) --once

test:
	python -m src.main --config $(CONFIG) --test

screenshot:
	python -m src.main --config config.example.yaml --test

lookup:
	python -m src.lookup --config $(CONFIG) $(ARGS)
