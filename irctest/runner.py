import collections
from typing import Dict, Union
import unittest


class NotImplementedByController(unittest.SkipTest, NotImplementedError):
    def __str__(self) -> str:
        return "Not implemented by controller: {}".format(self.args[0])


class ImplementationChoice(unittest.SkipTest):
    def __str__(self) -> str:
        return (
            "Choice in the implementation makes it impossible to "
            "perform a test: {}".format(self.args[0])
        )


class OptionalExtensionNotSupported(unittest.SkipTest):
    def __str__(self) -> str:
        return "Unsupported extension: {}".format(self.args[0])


class OptionalSaslMechanismNotSupported(unittest.SkipTest):
    def __str__(self) -> str:
        return "Unsupported SASL mechanism: {}".format(self.args[0])


class CapabilityNotSupported(unittest.SkipTest):
    def __str__(self) -> str:
        return "Unsupported capability: {}".format(self.args[0])


class IsupportTokenNotSupported(unittest.SkipTest):
    def __str__(self) -> str:
        return "Unsupported ISUPPORT token: {}".format(self.args[0])


class ChannelModeNotSupported(unittest.SkipTest):
    def __str__(self) -> str:
        return "Unsupported channel mode: {} ({})".format(self.args[0], self.args[1])


class ExtbanNotSupported(unittest.SkipTest):
    def __str__(self) -> str:
        return "Unsupported extban: {} ({})".format(self.args[0], self.args[1])


class NotRequiredBySpecifications(unittest.SkipTest):
    def __str__(self) -> str:
        return "Tests not required by the set of tested specification(s)."


class SkipStrictTest(unittest.SkipTest):
    def __str__(self) -> str:
        return "Tests not required because strict tests are disabled."


class TextTestResult(unittest.TextTestResult):
    def getDescription(self, test: unittest.TestCase) -> str:
        if hasattr(test, "description"):
            doc_first_lines = test.description()  # type: ignore
        else:
            doc_first_lines = test.shortDescription()
        return "\n".join((str(test), doc_first_lines or ""))


class TextTestRunner(unittest.TextTestRunner):
    """Small wrapper around unittest.TextTestRunner that reports the
    number of tests that were skipped because the software does not support
    an optional feature."""

    resultclass = TextTestResult

    def run(
        self, test: Union[unittest.TestSuite, unittest.TestCase]
    ) -> unittest.TestResult:
        result = super().run(test)
        assert self.resultclass is TextTestResult
        if result.skipped:
            print()
            print(
                "Some tests were skipped because the following optional "
                "specifications/mechanisms are not supported:"
            )
            msg_to_count: Dict[str, int] = collections.defaultdict(lambda: 0)
            for (test, msg) in result.skipped:
                msg_to_count[msg] += 1
            for (msg, count) in sorted(msg_to_count.items()):
                print("\t{} ({} test(s))".format(msg, count))
        return result
