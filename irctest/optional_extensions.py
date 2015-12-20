import unittest
import operator
import itertools

class OptionalExtensionNotSupported(unittest.SkipTest):
    def __str__(self):
        return 'Unsupported extension: {}'.format(self.args[0])

class OptionalSaslMechanismNotSupported(unittest.SkipTest):
    def __str__(self):
        return 'Unsupported SASL mechanism: {}'.format(self.args[0])

class OptionalityReportingTextTestRunner(unittest.TextTestRunner):
    def run(self, test):
        result = super().run(test)
        if result.skipped:
            print()
            print('Some tests were skipped because the following optional'
                    'specifications/mechanisms are not supported:')
            msg_to_tests = itertools.groupby(result.skipped,
                    key=operator.itemgetter(1))
            for (msg, tests) in msg_to_tests:
                print('\t{} ({} test(s))'.format(msg, sum(1 for x in tests)))
        return result
