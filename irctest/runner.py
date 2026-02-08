import unittest

from irctest.specifications import IsupportTokens, OptionalBehaviors


class NotImplementedByController(unittest.SkipTest, NotImplementedError):
    def __str__(self) -> str:
        return "Not implemented by controller: {}".format(self.args[0])


class ImplementationChoice(unittest.SkipTest):
    def __str__(self) -> str:
        return (
            "Choice in the implementation makes it impossible to "
            "perform a test: {}".format(self.args[0])
        )


class OptionalBehaviorNotSupported(unittest.SkipTest):
    def __init__(self, reason: OptionalBehaviors) -> None:
        super().__init__(reason)

    def __str__(self) -> str:
        return f"Optional behavior not supported: {self.args[0].value}"


class OptionalCommandNotSupported(unittest.SkipTest):
    def __str__(self) -> str:
        return "Unsupported command: {}".format(self.args[0])


class OptionalSaslMechanismNotSupported(unittest.SkipTest):
    def __str__(self) -> str:
        return "Unsupported SASL mechanism: {}".format(self.args[0])


class CapabilityNotSupported(unittest.SkipTest):
    def __str__(self) -> str:
        return "Unsupported capability: {}".format(self.args[0])


class IsupportTokenNotSupported(unittest.SkipTest):
    def __init__(self, reason: IsupportTokens) -> None:
        super().__init__(reason)

    def __str__(self) -> str:
        return f"Unsupported ISUPPORT token: {self.args[0].value}"


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
