.PHONY: all flakes oragono

all: flakes oragono

flakes:
	pyflakes3 ./irctest/cases.py ./irctest/client_mock.py ./irctest/controllers/oragono.py irctest/server_tests/*.py

ergo:
	python3 -m pytest -k "not deprecated" --controller irctest.controllers.ergo
