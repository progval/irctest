from irctest import cases


class ListTestCase(cases.BaseServerTestCase):
    @cases.mark_specifications("RFC1459", "RFC2812")
    def testListEmpty(self):
        """<https://tools.ietf.org/html/rfc1459#section-4.2.6>
        <https://tools.ietf.org/html/rfc2812#section-3.2.6>
        """
        self.connectClient("foo")
        self.connectClient("bar")
        self.getMessages(1)
        self.sendLine(2, "LIST")
        m = self.getMessage(2)
        if m.command == "321":
            # skip RPL_LISTSTART
            m = self.getMessage(2)
        while m.command == "322" and m.params[1] == "&SERVER":
            # ngircd adds this pseudo-channel
            m = self.getMessage(2)
        self.assertNotEqual(
            m.command,
            "322",  # RPL_LIST
            "LIST response gives (at least) one channel, whereas there " "is none.",
        )
        self.assertMessageMatch(
            m,
            command="323",  # RPL_LISTEND
            fail_msg="Second reply to LIST is not 322 (RPL_LIST) "
            "or 323 (RPL_LISTEND), or but: {msg}",
        )

    @cases.mark_specifications("RFC1459", "RFC2812")
    def testListOne(self):
        """When a channel exists, LIST should get it in a reply.
        <https://tools.ietf.org/html/rfc1459#section-4.2.6>
        <https://tools.ietf.org/html/rfc2812#section-3.2.6>
        """
        self.connectClient("foo")
        self.connectClient("bar")
        self.sendLine(1, "JOIN #chan")
        self.getMessages(1)
        self.sendLine(2, "LIST")
        m = self.getMessage(2)
        if m.command == "321":
            # skip RPL_LISTSTART
            m = self.getMessage(2)
        self.assertNotEqual(
            m.command,
            "323",  # RPL_LISTEND
            fail_msg="LIST response ended (ie. 323, aka RPL_LISTEND) "
            "without listing any channel, whereas there is one.",
        )
        self.assertMessageMatch(
            m,
            command="322",  # RPL_LIST
            fail_msg="Second reply to LIST is not 322 (RPL_LIST), "
            "nor 323 (RPL_LISTEND) but: {msg}",
        )
        m = self.getMessage(2)
        while m.command == "322" and m.params[1] == "&SERVER":
            # ngircd adds this pseudo-channel
            m = self.getMessage(2)
        self.assertNotEqual(
            m.command,
            "322",  # RPL_LIST
            fail_msg="LIST response gives (at least) two channels, "
            "whereas there is only one.",
        )
        self.assertMessageMatch(
            m,
            command="323",  # RPL_LISTEND
            fail_msg="Third reply to LIST is not 322 (RPL_LIST) "
            "or 323 (RPL_LISTEND), or but: {msg}",
        )
