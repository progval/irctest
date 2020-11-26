"""
https://ircv3.net/specs/extensions/message-tags.html
"""

from irctest import cases
from irctest.irc_utils.message_parser import parse_message

class MessageTagsTestCase(cases.BaseServerTestCase, cases.OptionalityHelper):

    @cases.SpecificationSelector.requiredBySpecification('message-tags')
    def testBasic(self):
        def getAllMessages():
            for name in ['alice', 'bob', 'carol']:
                self.getMessages(name)

        def assertNoTags(line):
            # tags start with '@', without tags we start with the prefix,
            # which begins with ':'
            self.assertEqual(line[0], ':')
            msg = parse_message(line)
            self.assertEqual(msg.tags, {})
            return msg

        self.connectClient('alice', name='alice', capabilities=['message-tags'])
        self.joinChannel('alice', '#test')
        self.connectClient('bob', name='bob', capabilities=['message-tags', 'echo-message'])
        self.joinChannel('bob', '#test')
        self.connectClient('carol', name='carol')
        self.joinChannel('carol', '#test')
        getAllMessages()

        self.sendLine('alice', '@+baz=bat;fizz=buzz PRIVMSG #test hi')
        self.getMessages('alice')
        bob_msg = self.getMessage('bob')
        carol_line = self.getMessage('carol', raw=True)
        self.assertMessageEqual(bob_msg, command='PRIVMSG', params=['#test', 'hi'])
        self.assertEqual(bob_msg.tags['+baz'], "bat")
        self.assertIn('msgid', bob_msg.tags)
        # should not relay a non-client-only tag
        self.assertNotIn('fizz', bob_msg.tags)
        # carol MUST NOT receive tags
        carol_msg = assertNoTags(carol_line)
        self.assertMessageEqual(carol_msg, command='PRIVMSG', params=['#test', 'hi'])
        getAllMessages()

        self.sendLine('bob', '@+bat=baz;+fizz=buzz PRIVMSG #test :hi yourself')
        bob_msg = self.getMessage('bob') # bob has echo-message
        alice_msg = self.getMessage('alice')
        carol_line = self.getMessage('carol', raw=True)
        carol_msg = assertNoTags(carol_line)
        for msg in [alice_msg, bob_msg, carol_msg]:
            self.assertMessageEqual(msg, command='PRIVMSG', params=['#test', 'hi yourself'])
        for msg in [alice_msg, bob_msg]:
            self.assertEqual(msg.tags['+bat'], 'baz')
            self.assertEqual(msg.tags['+fizz'], 'buzz')
        self.assertTrue(alice_msg.tags['msgid'])
        self.assertEqual(alice_msg.tags['msgid'], bob_msg.tags['msgid'])

        # test TAGMSG and basic escaping
        self.sendLine('bob', '@+buzz=fizz\:buzz;cat=dog;+steel=wootz TAGMSG #test')
        bob_msg = self.getMessage('bob') # bob has echo-message
        alice_msg = self.getMessage('alice')
        # carol MUST NOT receive TAGMSG at all
        self.assertEqual(self.getMessages('carol'), [])
        for msg in [alice_msg, bob_msg]:
            self.assertMessageEqual(alice_msg, command='TAGMSG', params=['#test'])
            self.assertEqual(msg.tags['+buzz'], 'fizz;buzz')
            self.assertEqual(msg.tags['+steel'], 'wootz')
            self.assertNotIn('cat', msg.tags)
        self.assertTrue(alice_msg.tags['msgid'])
        self.assertEqual(alice_msg.tags['msgid'], bob_msg.tags['msgid'])
