"""
Channel casemapping
"""

import pytest

from irctest import cases, client_mock, runner


class ChannelCaseSensitivityTestCase(cases.BaseServerTestCase):
    @pytest.mark.parametrize(
        "casemapping,name1,name2",
        [
            ("ascii", "#Foo", "#foo"),
            ("rfc1459", "#Foo", "#foo"),
            ("rfc1459", "#F]|oo{", "#f}\\oo["),
            ("rfc1459", "#F}o\\o[", "#f]o|o{"),
        ],
    )
    @cases.mark_specifications("RFC1459", "RFC2812", strict=True)
    def testChannelsEquivalent(self, casemapping, name1, name2):
        self.connectClient("foo")
        self.connectClient("bar")
        if self.server_support["CASEMAPPING"] != casemapping:
            raise runner.NotImplementedByController(
                "Casemapping {} not implemented".format(casemapping)
            )
        self.joinClient(1, name1)
        self.joinClient(2, name2)
        try:
            m = self.getMessage(1)
            self.assertMessageMatch(m, command="JOIN", nick="bar")
        except client_mock.NoMessageException:
            raise AssertionError(
                "Channel names {} and {} are not equivalent.".format(name1, name2)
            )

    @pytest.mark.parametrize(
        "casemapping,name1,name2",
        [
            ("ascii", "#Foo", "#fooa"),
            ("rfc1459", "#Foo", "#fooa"),
        ],
    )
    @cases.mark_specifications("RFC1459", "RFC2812", strict=True)
    def testChannelsNotEquivalent(self, casemapping, name1, name2):
        self.connectClient("foo")
        self.connectClient("bar")
        if self.server_support["CASEMAPPING"] != casemapping:
            raise runner.NotImplementedByController(
                "Casemapping {} not implemented".format(casemapping)
            )
        self.joinClient(1, name1)
        self.joinClient(2, name2)
        try:
            m = self.getMessage(1)
        except client_mock.NoMessageException:
            pass
        else:
            self.assertMessageMatch(
                m, command="JOIN", nick="bar"
            )  # This should always be true
            raise AssertionError(
                "Channel names {} and {} are equivalent.".format(name1, name2)
            )
