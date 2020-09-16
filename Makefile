.PHONY: all flakes integration

all: flakes integration

flakes:
	pyflakes3 ./irctest/cases.py ./irctest/client_mock.py ./irctest/controllers/oragono.py irctest/server_tests/*.py

integration:
	./test.py irctest.controllers.oragono
