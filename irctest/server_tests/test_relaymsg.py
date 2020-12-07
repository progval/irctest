from irctest import cases
from irctest.irc_utils.junkdrawer import random_name
from irctest.server_tests.test_chathistory import CHATHISTORY_CAP, EVENT_PLAYBACK_CAP


RELAYMSG_CAP = 'draft/relaymsg'

class RelaymsgTestCase(cases.BaseServerTestCase):

    def customizedConfig(self):
        return self.controller.addMysqlToConfig()

    @cases.SpecificationSelector.requiredBySpecification('Oragono')
    def testRelaymsg(self):
        self.connectClient('baz', name='baz', capabilities=['server-time', 'message-tags', 'batch', 'labeled-response', 'echo-message', CHATHISTORY_CAP, EVENT_PLAYBACK_CAP])
        self.connectClient('qux', name='qux', capabilities=['server-time', 'message-tags', 'batch', 'labeled-response', 'echo-message', CHATHISTORY_CAP, EVENT_PLAYBACK_CAP])
        chname = random_name('#relaymsg')
        self.joinChannel('baz', chname)
        self.joinChannel('qux', chname)
        self.getMessages('baz')
        self.getMessages('qux')

        self.sendLine('baz', 'RELAYMSG %s invalid!nick/discord hi' % (chname,))
        response = self.getMessages('baz')[0]
        self.assertEqual(response.command, 'FAIL')
        self.assertEqual(response.params[:2], ['RELAYMSG', 'INVALID_NICK'])

        self.sendLine('baz', 'RELAYMSG %s regular_nick hi' % (chname,))
        response = self.getMessages('baz')[0]
        self.assertEqual(response.command, 'FAIL')
        self.assertEqual(response.params[:2], ['RELAYMSG', 'INVALID_NICK'])

        self.sendLine('baz', 'RELAYMSG %s smt/discord hi' % (chname,))
        response = self.getMessages('baz')[0]
        self.assertMessageEqual(response, nick='smt/discord', command='PRIVMSG', params=[chname, 'hi'])
        relayed_msg = self.getMessages('qux')[0]
        self.assertMessageEqual(relayed_msg, nick='smt/discord', command='PRIVMSG', params=[chname, 'hi'])

        # labeled-response
        self.sendLine('baz', '@label=x RELAYMSG %s smt/discord :hi again' % (chname,))
        response = self.getMessages('baz')[0]
        self.assertMessageEqual(response, nick='smt/discord', command='PRIVMSG', params=[chname, 'hi again'])
        self.assertEqual(response.tags.get('label'), 'x')
        relayed_msg = self.getMessages('qux')[0]
        self.assertMessageEqual(relayed_msg, nick='smt/discord', command='PRIVMSG', params=[chname, 'hi again'])

        self.sendLine('qux', 'RELAYMSG %s smt/discord :hi a third time' % (chname,))
        response = self.getMessages('qux')[0]
        self.assertEqual(response.command, 'FAIL')
        self.assertEqual(response.params[:2], ['RELAYMSG', 'PRIVS_NEEDED'])

        # grant qux chanop, allowing relaymsg
        self.sendLine('baz', 'MODE %s +o qux' % (chname,))
        self.getMessages('baz')
        self.getMessages('qux')
        # give baz the relaymsg cap
        self.sendLine('baz', 'CAP REQ %s' % (RELAYMSG_CAP))
        self.assertMessageEqual(self.getMessages('baz')[0], command='CAP', params=['baz', 'ACK', RELAYMSG_CAP])

        self.sendLine('qux', 'RELAYMSG %s smt/discord :hi a third time' % (chname,))
        response = self.getMessages('qux')[0]
        self.assertMessageEqual(response, nick='smt/discord', command='PRIVMSG', params=[chname, 'hi a third time'])
        relayed_msg = self.getMessages('baz')[0]
        self.assertMessageEqual(relayed_msg, nick='smt/discord', command='PRIVMSG', params=[chname, 'hi a third time'])
        self.assertEqual(relayed_msg.tags.get('relaymsg'), 'qux')

        self.sendLine('baz', 'CHATHISTORY LATEST %s * 10' % (chname,))
        messages = self.getMessages('baz')
        self.assertEqual([msg.params[-1] for msg in messages if msg.command == 'PRIVMSG'], ['hi', 'hi again', 'hi a third time'])
