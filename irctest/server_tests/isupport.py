"""
RPL_ISUPPORT: `format <https://modern.ircdocs.horse/#rplisupport-005>`__
and various `tokens <https://modern.ircdocs.horse/#rplisupport-parameters>`__
"""

import re

from irctest import cases, runner


class IsupportTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("Modern")
    @cases.mark_isupport("PREFIX")
    def testPrefix(self):
        """https://modern.ircdocs.horse/#prefix-parameter"""
        self.connectClient("foo")

        if "PREFIX" not in self.server_support:
            raise runner.IsupportTokenNotSupported("PREFIX")

        if self.server_support["PREFIX"] == "":
            # "The value is OPTIONAL and when it is not specified indicates that no
            # prefixes are supported."
            return

        m = re.match(
            r"\((?P<modes>[a-zA-Z]+)\)(?P<prefixes>\S+)", self.server_support["PREFIX"]
        )
        self.assertTrue(
            m,
            f"PREFIX={self.server_support['PREFIX']} does not have the expected "
            f"format.",
        )

        modes = m.group("modes")
        prefixes = m.group("prefixes")

        # "There is a one-to-one mapping between prefixes and channel modes."
        self.assertEqual(
            len(modes), len(prefixes), "Mismatched length of prefix and channel modes."
        )

        # "The prefixes in this parameter are in descending order, from the prefix
        # that gives the most privileges to the prefix that gives the least."
        self.assertLess(modes.index("o"), modes.index("v"), "'o' is not before 'v'")
        if "h" in modes:
            self.assertLess(modes.index("o"), modes.index("h"), "'o' is not before 'h'")
            self.assertLess(modes.index("h"), modes.index("v"), "'h' is not before 'v'")
        if "q" in modes:
            self.assertLess(modes.index("q"), modes.index("o"), "'q' is not before 'o'")

        # Not technically in the spec, but it would be very confusing not to follow
        # these conventions.
        mode_to_prefix = dict(zip(modes, prefixes))
        self.assertEqual(mode_to_prefix["o"], "@", "Prefix char for mode +o is not @")
        self.assertEqual(mode_to_prefix["v"], "+", "Prefix char for mode +v is not +")
        if "h" in modes:
            self.assertEqual(
                mode_to_prefix["h"], "%", "Prefix char for mode +h is not %"
            )
        if "q" in modes:
            self.assertEqual(
                mode_to_prefix["q"], "~", "Prefix char for mode +q is not ~"
            )
        if "a" in modes:
            self.assertEqual(
                mode_to_prefix["a"], "&", "Prefix char for mode +a is not &"
            )

    @cases.mark_specifications("Modern", "ircdocs")
    @cases.mark_isupport("TARGMAX")
    def testTargmax(self):
        """
        "Format: TARGMAX=[<command>:[limit]{,<command>:[limit]}]"
        -- https://modern.ircdocs.horse/#targmax-parameter

        "TARGMAX=[cmd:[number][,cmd:[number][,...]]]"
        -- https://defs.ircdocs.horse/defs/isupport.html#targmax
        """
        self.connectClient("foo")

        if "TARGMAX" not in self.server_support:
            raise runner.IsupportTokenNotSupported("TARGMAX")

        parts = self.server_support["TARGMAX"].split(",")
        for part in parts:
            self.assertTrue(
                re.match("[A-Z]+:[0-9]*", part), "Invalid TARGMAX key:value: %r", part
            )
