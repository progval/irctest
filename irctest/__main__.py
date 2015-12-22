import sys
import unittest
import argparse
import unittest
import functools
import importlib
from .cases import _IrcTestCase
from .runner import TextTestRunner
from .basecontrollers import BaseClientController, BaseServerController

def main(args):
    try:
        module = importlib.import_module(args.module)
    except ImportError:
        print('Cannot import module {}'.format(args.module), file=sys.stderr)
        exit(1)

    controller_class = module.get_irctest_controller_class()
    if issubclass(controller_class, BaseClientController):
        import irctest.client_tests as module
    elif issubclass(controller_class, BaseServerController):
        import irctest.server_tests as module
    else:
        print(r'{}.Controller should be a subclass of '
                r'irctest.basecontroller.Base{{Client,Server}}Controller'
                .format(args.module),
                file=sys.stderr)
        exit(1)
    _IrcTestCase.controllerClass = controller_class
    _IrcTestCase.show_io = args.show_io
    ts = module.discover()
    testRunner = TextTestRunner(
            verbosity=args.verbose,
            descriptions=True,
            )
    testLoader = unittest.loader.defaultTestLoader
    testRunner.run(ts)


parser = argparse.ArgumentParser(
        description='A script to test interoperability of IRC software.')
parser.add_argument('module', type=str,
        help='The module used to run the tested program.')
parser.add_argument('--show-io', action='store_true',
        help='Show input/outputs with the tested program.')
parser.add_argument('-v', '--verbose', action='count', default=1,
        help='Verbosity.')


args = parser.parse_args()
main(args)
