"""
draft/multiline
"""

from irctest import cases

CAP_NAME   = 'draft/multiline'
BATCH_TYPE = 'draft/multiline'
CONCAT_TAG = 'draft/multiline-concat'

base_caps = ['message-tags', 'batch', 'echo-message', 'server-time', 'labeled-response']

class MultilineTestCase(cases.BaseServerTestCase, cases.OptionalityHelper):

    @cases.SpecificationSelector.requiredBySpecification('Oragono')
    def testBasic(self):
        self.connectClient('alice', capabilities=(base_caps + [CAP_NAME]))
        self.joinChannel(1, '#test')
        self.connectClient('bob', capabilities=(base_caps + [CAP_NAME]))
        self.joinChannel(2, '#test')
        self.connectClient('charlie', capabilities=base_caps)
        self.joinChannel(3, '#test')

        self.getMessages(1)
        self.getMessages(2)
        self.getMessages(3)

        self.sendLine(1, '@label=xyz BATCH +123 %s #test' % (BATCH_TYPE,))
        self.sendLine(1, '@batch=123 PRIVMSG #test hello')
        self.sendLine(1, '@batch=123 PRIVMSG #test :#how is ')
        self.sendLine(1, '@batch=123;%s PRIVMSG #test :everyone?' % (CONCAT_TAG,))
        self.sendLine(1, 'BATCH -123')

        echo = self.getMessages(1)
        batchStart, batchEnd = echo[0], echo[-1]
        self.assertEqual(batchStart.command, 'BATCH')
        self.assertEqual(batchStart.tags.get('label'), 'xyz')
        self.assertEqual(len(batchStart.params), 3)
        self.assertEqual(batchStart.params[1], CAP_NAME)
        self.assertEqual(batchStart.params[2], "#test")
        self.assertEqual(batchEnd.command, 'BATCH')
        self.assertEqual(batchStart.params[0][1:], batchEnd.params[0][1:])
        msgid = batchStart.tags.get('msgid')
        time = batchStart.tags.get('time')
        assert msgid
        assert time
        privmsgs = echo[1:-1]
        for msg in privmsgs:
            self.assertMessageEqual(msg, command='PRIVMSG')
            self.assertNotIn('msgid', msg.tags)
            self.assertNotIn('time', msg.tags)
        self.assertIn(CONCAT_TAG, echo[3].tags)

        relay = self.getMessages(2)
        batchStart, batchEnd = relay[0], relay[-1]
        self.assertEqual(batchStart.command, 'BATCH')
        self.assertEqual(batchEnd.command, 'BATCH')
        self.assertEqual(batchStart.params[0][1:], batchEnd.params[0][1:])
        self.assertEqual(batchStart.tags.get('msgid'), msgid)
        self.assertEqual(batchStart.tags.get('time'), time)
        privmsgs = relay[1:-1]
        for msg in privmsgs:
            self.assertMessageEqual(msg, command='PRIVMSG')
            self.assertNotIn('msgid', msg.tags)
            self.assertNotIn('time', msg.tags)
        self.assertIn(CONCAT_TAG, relay[3].tags)

        fallback_relay = self.getMessages(3)
        relayed_fmsgids = []
        for msg in fallback_relay:
            self.assertMessageEqual(msg, command='PRIVMSG')
            relayed_fmsgids.append(msg.tags.get('msgid'))
            self.assertEqual(msg.tags.get('time'), time)
            self.assertNotIn(CONCAT_TAG, msg.tags)
        self.assertEqual(relayed_fmsgids, [msgid] + [None]*(len(fallback_relay)-1))
