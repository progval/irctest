"""
Regression tests for bugs in oragono.
"""

from irctest import cases

class RegressionsTestCase(cases.BaseServerTestCase):

    @cases.SpecificationSelector.requiredBySpecification('RFC1459')
    def testFailedNickChange(self):
        # see oragono commit d0ded906d4ac8f
        self.connectClient('alice')
        self.connectClient('bob')

        # bob tries to change to an in-use nickname; this MUST fail
        self.sendLine(2, 'NICK alice')
        ms = self.getMessages(2)
        self.assertEqual(len(ms), 1)
        self.assertMessageEqual(ms[0], command='433') # ERR_NICKNAMEINUSE

        # bob MUST still own the bob nick, and be able to receive PRIVMSG as bob
        self.sendLine(1, 'PRIVMSG bob hi')
        ms = self.getMessages(1)
        self.assertEqual(len(ms), 0)
        ms = self.getMessages(2)
        self.assertEqual(len(ms), 1)
        self.assertMessageEqual(ms[0], command='PRIVMSG', params=['bob', 'hi'])

    @cases.SpecificationSelector.requiredBySpecification('RFC1459')
    def testCaseChanges(self):
        self.connectClient('alice')
        self.joinChannel(1, '#test')
        self.connectClient('bob')
        self.joinChannel(2, '#test')
        self.getMessages(1)
        self.getMessages(2)

        # case change: both alice and bob should get a successful nick line
        self.sendLine(1, 'NICK Alice')
        ms = self.getMessages(1)
        self.assertEqual(len(ms), 1)
        self.assertMessageEqual(ms[0], command='NICK', params=['Alice'])
        ms = self.getMessages(2)
        self.assertEqual(len(ms), 1)
        self.assertMessageEqual(ms[0], command='NICK', params=['Alice'])

        # bob should not get notified on no-op nick change
        self.sendLine(1, 'NICK Alice')
        ms = self.getMessages(2)
        self.assertEqual(ms, [])

    @cases.SpecificationSelector.requiredBySpecification('IRCv3.2')
    def testTagCap(self):
        # regression test for oragono #754
        self.connectClient('alice', capabilities=['message-tags', 'batch', 'echo-message', 'server-time'])
        self.connectClient('bob')
        self.getMessages(1)
        self.getMessages(2)

        self.sendLine(1, '@+draft/reply=ct95w3xemz8qj9du2h74wp8pee PRIVMSG bob :hey yourself')
        ms = self.getMessages(1)
        self.assertEqual(len(ms), 1)
        self.assertMessageEqual(ms[0], command='PRIVMSG', params=['bob', 'hey yourself'])
        self.assertEqual(ms[0].tags.get('+draft/reply'), 'ct95w3xemz8qj9du2h74wp8pee')

        ms = self.getMessages(2)
        self.assertEqual(len(ms), 1)
        self.assertMessageEqual(ms[0], command='PRIVMSG', params=['bob', 'hey yourself'])
        self.assertEqual(ms[0].tags, {})

        self.sendLine(2, 'CAP REQ :message-tags server-time')
        self.getMessages(2)
        self.sendLine(1, '@+draft/reply=tbxqauh9nykrtpa3n6icd9whan PRIVMSG bob :hey again')
        self.getMessages(1)
        ms = self.getMessages(2)
        # now bob has the tags cap, so he should receive the tags
        self.assertEqual(len(ms), 1)
        self.assertMessageEqual(ms[0], command='PRIVMSG', params=['bob', 'hey again'])
        self.assertEqual(ms[0].tags.get('+draft/reply'), 'tbxqauh9nykrtpa3n6icd9whan')
