import importlib
import sys
import unittest

import _pytest.unittest
import pytest

from irctest.basecontrollers import BaseClientController, BaseServerController
from irctest.cases import BaseClientTestCase, BaseServerTestCase, _IrcTestCase


def pytest_addoption(parser):
    """Called by pytest, registers CLI options passed to the pytest command."""
    parser.addoption(
        "--controller", help="Which module to use to run the tested software."
    )
    parser.addoption(
        "--openssl-bin", type=str, default="openssl", help="The openssl binary to use"
    )


def pytest_configure(config):
    """Called by pytest, after it parsed the command-line."""
    module_name = config.getoption("controller")

    if module_name is None:
        pytest.exit("--controller is required.", 1)

    try:
        module = importlib.import_module(module_name)
    except ImportError:
        pytest.exit("Cannot import module {}".format(module_name), 1)

    controller_class = module.get_irctest_controller_class()
    if issubclass(controller_class, BaseClientController):
        from irctest import client_tests as module
    elif issubclass(controller_class, BaseServerController):
        from irctest import server_tests as module
    else:
        pytest.exit(
            r"{}.Controller should be a subclass of "
            r"irctest.basecontroller.Base{{Client,Server}}Controller".format(
                module_name
            ),
            1,
        )
    _IrcTestCase.controllerClass = controller_class
    _IrcTestCase.controllerClass.openssl_bin = config.getoption("openssl_bin")
    _IrcTestCase.show_io = True  # TODO


def pytest_collection_modifyitems(session, config, items):
    """Called by pytest after finishing the test collection,
    and before actually running the tests.

    This function filters out client tests if running with a server controller,
    and vice versa.
    """

    # First, check if we should run server tests or client tests
    if issubclass(_IrcTestCase.controllerClass, BaseServerController):
        server_tests = True
    elif issubclass(_IrcTestCase.controllerClass, BaseClientController):
        server_tests = False
    else:
        assert False, (
            f"{_IrcTestCase.controllerClass} inherits neither "
            f"BaseClientController or BaseServerController"
        )

    filtered_items = []

    # Iterate over each of the test functions (they are pytest "Nodes")
    for item in items:
        # we only use unittest-style test function here
        assert isinstance(item, _pytest.unittest.TestCaseFunction)

        # unittest-style test functions have the node of UnitTest class as parent
        assert isinstance(item.parent, _pytest.unittest.UnitTestCase)

        # and that node references the UnitTest class
        assert issubclass(item.parent.cls, unittest.TestCase)

        # and in this project, TestCase classes all inherit either from BaseClientController
        # or BaseServerController.
        if issubclass(item.parent.cls, BaseServerTestCase):
            if server_tests:
                filtered_items.append(item)
        elif issubclass(item.parent.cls, BaseClientTestCase):
            if not server_tests:
                filtered_items.append(item)
        else:
            assert False, (
                f"{item}'s class inherits neither BaseServerTestCase "
                "or BaseClientTestCase"
            )

    # Finally, rewrite in-place the list of tests pytest will run
    items[:] = filtered_items
