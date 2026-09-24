.PHONY: init check

init:
	python3 -m src.bootstrap --database data/research-wife.db --schema schema.sql

check:
	python3 -m src.bootstrap --database /tmp/research-wife-check.db --schema schema.sql
