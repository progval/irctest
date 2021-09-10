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
