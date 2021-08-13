import re

from irctest import cases, runner


class IsupportTestCase(cases.BaseServerTestCase):
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
            raise runner.NotImplementedByController("TARGMAX")

        parts = self.server_support["TARGMAX"].split(",")
        for part in parts:
            self.assertTrue(
                re.match("[A-Z]+:[0-9]*", part), "Invalid TARGMAX key:value: %r", part
            )
