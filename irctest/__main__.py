import sys
import unittest
import argparse
import unittest
import functools
import importlib
from .cases import _IrcTestCase
from .runner import TextTestRunner
from .specifications import Specifications
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
    _IrcTestCase.controllerClass.openssl_bin = args.openssl_bin
    _IrcTestCase.show_io = args.show_io
    _IrcTestCase.strictTests = not args.loose
    if args.specification:
        try:
            _IrcTestCase.testedSpecifications = frozenset(
                Specifications.of_name(x) for x in args.specification
                )
        except ValueError:
            print('Invalid set of specifications: {}'
                    .format(', '.join(args.specification)))
            exit(1)
    else:
        _IrcTestCase.testedSpecifications = frozenset(
                Specifications)
    print('Testing {} on specification(s): {}'.format(
        controller_class.software_name,
        ', '.join(sorted(map(lambda x:x.value,
            _IrcTestCase.testedSpecifications)))))
    ts = module.discover()
    testRunner = TextTestRunner(
            verbosity=args.verbose,
            descriptions=True,
            )
    testLoader = unittest.loader.defaultTestLoader
    result = testRunner.run(ts)
    if result.failures or result.errors:
        exit(1)
    else:
        exit(0)


parser = argparse.ArgumentParser(
        description='A script to test interoperability of IRC software.')
parser.add_argument('module', type=str,
        help='The module used to run the tested program.')
parser.add_argument('--openssl-bin', type=str, default='openssl',
        help='The openssl binary to use')
parser.add_argument('--show-io', action='store_true',
        help='Show input/outputs with the tested program.')
parser.add_argument('-v', '--verbose', action='count', default=1,
        help='Verbosity. Give this option multiple times to make '
        'it even more verbose.')
parser.add_argument('-s', '--specification', type=str, action='append',
        help=('The set of specifications to test the program with. '
        'Valid values: {}. '
        'Use this option multiple times to test with multiple '
        'specifications. If it is not given, defaults to all.')
        .format(', '.join(x.value for x in Specifications)))
parser.add_argument('-l', '--loose', action='store_true',
        help='Disables strict checks of conformity to the specification. '
        'Strict means the specification is unclear, and the most restrictive '
        'interpretation is choosen.')


args = parser.parse_args()
main(args)
