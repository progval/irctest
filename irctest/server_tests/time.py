import math
import time

from irctest import cases
from irctest.numerics import RPL_TIME
from irctest.patma import ANYSTR, StrRe


class TimeTestCase(cases.BaseServerTestCase):
    def testTime(self):
        self.connectClient("user")

        time_before = math.floor(time.time())
        self.sendLine(1, "TIME")

        msg = self.getMessage(1)

        time_after = math.ceil(time.time())

        if len(msg.params) == 3:
            self.assertMessageMatch(
                msg, command=RPL_TIME, params=["user", "My.Little.Server", ANYSTR]
            )
        else:
            self.assertMessageMatch(
                msg,
                command=RPL_TIME,
                params=["user", "My.Little.Server", StrRe("[0-9]+"), "0", ANYSTR],
            )
            self.assertIn(
                int(msg.params[2]),
                range(time_before, time_after + 1),
                "Timestamp not in expected range",
            )
