.PHONY: install auth-gmail run dry-run test

install:
	python3 -m pip install -e ".[dev]"

auth-gmail:
	python3 -m trend_news auth-gmail

run:
	python3 -m trend_news run --config config/topics.yml

dry-run:
	python3 -m trend_news run --config config/topics.yml --dry-run

test:
	python3 -m pytest
