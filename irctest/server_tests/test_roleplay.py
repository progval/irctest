from irctest import cases
from irctest.numerics import ERR_CANNOTSENDRP
from irctest.irc_utils.random import random_name

class RoleplayTestCase(cases.BaseServerTestCase):

    def customizedConfig(self):
        config = self.controller.baseConfig()
        config['roleplay'] = {
            'enabled': True,
        }
        return self.controller.addMysqlToConfig(config)

    @cases.SpecificationSelector.requiredBySpecification('Oragono')
    def testRoleplay(self):
        bar = random_name('bar')
        qux = random_name('qux')
        chan = random_name('#chan')
        self.connectClient(bar, name=bar, capabilities=['batch', 'labeled-response', 'message-tags', 'server-time'])
        self.connectClient(qux, name=qux, capabilities=['batch', 'labeled-response', 'message-tags', 'server-time'])
        self.joinChannel(bar, chan)
        self.joinChannel(qux, chan)
        self.getMessages(bar)

        # roleplay should be forbidden because we aren't +E yet
        self.sendLine(bar, 'NPC %s bilbo too much bread' % (chan,))
        reply = self.getMessages(bar)[0]
        self.assertEqual(reply.command, ERR_CANNOTSENDRP)

        self.sendLine(bar, 'MODE %s +E' % (chan,))
        reply = self.getMessages(bar)[0]
        self.assertEqual(reply.command, 'MODE')
        self.assertMessageEqual(reply, command='MODE', params=[chan, '+E'])
        self.getMessages(qux)

        self.sendLine(bar, 'NPC %s bilbo too much bread' % (chan,))
        reply = self.getMessages(bar)[0]
        self.assertEqual(reply.command, 'PRIVMSG')
        self.assertEqual(reply.params[0], chan)
        self.assertTrue(reply.prefix.startswith('*bilbo*!'))
        self.assertIn('too much bread', reply.params[1])

        reply = self.getMessages(qux)[0]
        self.assertEqual(reply.command, 'PRIVMSG')
        self.assertEqual(reply.params[0], chan)
        self.assertTrue(reply.prefix.startswith('*bilbo*!'))
        self.assertIn('too much bread', reply.params[1])

        # test history storage
        self.sendLine(qux, 'CHATHISTORY LATEST %s * 10' % (chan,))
        reply = [msg for msg in self.getMessages(qux) if msg.command == 'PRIVMSG' and 'bilbo' in msg.prefix][0]
        self.assertEqual(reply.command, 'PRIVMSG')
        self.assertEqual(reply.params[0], chan)
        self.assertTrue(reply.prefix.startswith('*bilbo*!'))
        self.assertIn('too much bread', reply.params[1])
