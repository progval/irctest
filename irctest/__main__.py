import sys
import unittest
import argparse
import unittest
import functools
import importlib
from .cases import _IrcTestCase
from .basecontrollers import BaseClientController, BaseServerController

def main(args):
    try:
        module = importlib.import_module(args.module)
    except ImportError:
        print('Cannot import module {}'.format(args.module), file=sys.stderr)
        exit(1)

    controller_class = module.get_irctest_controller_class()
    if issubclass(controller_class, BaseClientController):
        module = 'irctest.clienttests'
    elif issubclass(controller_class, BaseClientController):
        module = 'irctest.servertests'
    else:
        print('{}.Controller should be a subclass of '
                'irctest.basecontroller.Base{Client,Server}Controller'
                .format(args.module),
                file=sys.stderr)
        exit(1)
    _IrcTestCase.controllerClass = controller_class
    unittest.main(module=module, argv=[sys.argv[0], 'discover'])


parser = argparse.ArgumentParser(
        description='A script to test interoperability of IRC software.')
parser.add_argument('module', type=str,
        help='The module used to run the tested program.')

args = parser.parse_args()
main(args)
