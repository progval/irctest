.PHONY: oragono

oragono:
	pyflakes3  ./irctest/controllers/oragono.py irctest/server_tests/*.py
	./test.py irctest.controllers.oragono
