.PHONY: oragono

oragono:
	pyflakes3 ./irctest/cases.py ./irctest/client_mock.py ./irctest/controllers/oragono.py irctest/server_tests/*.py
	./test.py irctest.controllers.oragono
