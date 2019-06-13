"""
<https://github.com/DanielOaks/ircv3-specifications/blob/master+resume/extensions/resume.md>
"""

from irctest import cases

from irctest.numerics import RPL_AWAY

ANCIENT_TIMESTAMP = '2006-01-02T15:04:05.999Z'

class ResumeTestCase(cases.BaseServerTestCase):

    @cases.SpecificationSelector.requiredBySpecification('Oragono')
    def testNoResumeByDefault(self):
        self.connectClient('bar', capabilities=['batch', 'echo-message', 'draft/labeled-response-0.2'])
        ms = self.getMessages(1)
        resume_messages = [m for m in ms if m.command == 'RESUME']
        self.assertEqual(resume_messages, [], 'should not see RESUME messages unless explicitly negotiated')

    @cases.SpecificationSelector.requiredBySpecification('Oragono')
    def testResume(self):
        self.connectClient('bar', capabilities=['batch', 'draft/labeled-response-0.2', 'server-time'])
        ms = self.getMessages(1)

        welcome = self.connectClient('baz', capabilities=['batch', 'draft/labeled-response-0.2', 'server-time', 'draft/resume-0.5'])
        resume_messages = [m for m in welcome if m.command == 'RESUME']
        self.assertEqual(len(resume_messages), 1)
        self.assertEqual(resume_messages[0].params[0], 'TOKEN')
        token = resume_messages[0].params[1]

        self.joinChannel(1, '#xyz')
        self.joinChannel(2, '#xyz')
        self.sendLine(1, 'PRIVMSG #xyz :hello friends')
        self.sendLine(1, 'PRIVMSG baz :hello friend singular')
        self.getMessages(1)
        # should receive these messages
        privmsgs = [m for m in self.getMessages(2) if m.command == 'PRIVMSG']
        self.assertEqual(len(privmsgs), 2)
        privmsgs.sort(key=lambda m: m.params[0])
        self.assertMessageEqual(privmsgs[0], command='PRIVMSG', params=['#xyz', 'hello friends'])
        self.assertMessageEqual(privmsgs[1], command='PRIVMSG', params=['baz', 'hello friend singular'])
        channelMsgTime = privmsgs[0].tags.get('time')

        # tokens MUST be cryptographically secure; therefore, this token should be invalid
        # with probability at least 1 - 1/(2**128)
        bad_token = 'a' * len(token)
        self.addClient()
        self.sendLine(3, 'CAP LS')
        self.sendLine(3, 'CAP REQ :batch draft/labeled-response-0.2 server-time draft/resume-0.5')
        self.sendLine(3, 'NICK tempnick')
        self.sendLine(3, 'USER tempuser 0 * tempuser')
        self.sendLine(3, ' '.join(('RESUME', bad_token, ANCIENT_TIMESTAMP)))

        # resume with a bad token MUST fail
        ms = self.getMessages(3)
        resume_err_messages = [m for m in ms if m.command == 'FAIL' and m.params[:2] == ['RESUME', 'INVALID_TOKEN']]
        self.assertEqual(len(resume_err_messages), 1)
        # however, registration should proceed with the alternative nick
        self.sendLine(3, 'CAP END')
        welcome_msgs = [m for m in self.getMessages(3) if m.command == '001'] # RPL_WELCOME
        self.assertEqual(welcome_msgs[0].params[0], 'tempnick')

        self.addClient()
        self.sendLine(4, 'CAP LS')
        self.sendLine(4, 'CAP REQ :batch draft/labeled-response-0.2 server-time draft/resume-0.5')
        self.sendLine(4, 'NICK tempnick_')
        self.sendLine(4, 'USER tempuser 0 * tempuser')
        # resume with a timestamp in the distant past
        self.sendLine(4, ' '.join(('RESUME', token, ANCIENT_TIMESTAMP)))
        # successful resume does not require CAP END:
        # https://github.com/ircv3/ircv3-specifications/pull/306/files#r255318883
        ms = self.getMessages(4)

        # now, do a valid resume with the correct token
        resume_messages = [m for m in ms if m.command == 'RESUME']
        self.assertEqual(len(resume_messages), 2)
        self.assertEqual(resume_messages[0].params[0], 'TOKEN')
        new_token = resume_messages[0].params[1]
        self.assertNotEqual(token, new_token, 'should receive a new, strong resume token; instead got ' + new_token)
        # success message
        self.assertMessageEqual(resume_messages[1], command='RESUME', params=['SUCCESS', 'baz'])

        # test replay of messages
        privmsgs = [m for m in ms if m.command == 'PRIVMSG' and m.prefix.startswith('bar')]
        self.assertEqual(len(privmsgs), 2)
        privmsgs.sort(key=lambda m: m.params[0])
        self.assertMessageEqual(privmsgs[0], command='PRIVMSG', params=['#xyz', 'hello friends'])
        self.assertMessageEqual(privmsgs[1], command='PRIVMSG', params=['baz', 'hello friend singular'])
        # should replay with the original server-time
        # TODO this probably isn't testing anything because the timestamp only has second resolution,
        # hence will typically match by accident
        self.assertEqual(privmsgs[0].tags.get('time'), channelMsgTime)

        # legacy client should receive a QUIT and a JOIN
        quit, join = [m for m in self.getMessages(1) if m.command in ('QUIT', 'JOIN')]
        self.assertEqual(quit.command, 'QUIT')
        self.assertTrue(quit.prefix.startswith('baz'))
        self.assertMessageEqual(join, command='JOIN', params=['#xyz'])
        self.assertTrue(join.prefix.startswith('baz'))

        # original client should have been disconnected
        self.assertDisconnected(2)
        # new client should be receiving PRIVMSG sent to baz
        self.sendLine(1, 'PRIVMSG baz :hello again')
        self.getMessages(1)
        self.assertMessageEqual(self.getMessage(4), command='PRIVMSG', params=['baz', 'hello again'])

        # test chain-resuming (resuming the resumed connection, using the new token)
        self.addClient()
        self.sendLine(5, 'CAP LS')
        self.sendLine(5, 'CAP REQ :batch draft/labeled-response-0.2 server-time draft/resume-0.5')
        self.sendLine(5, 'NICK tempnick_')
        self.sendLine(5, 'USER tempuser 0 * tempuser')
        self.sendLine(5, 'RESUME ' + new_token)
        ms = self.getMessages(5)

        resume_messages = [m for m in ms if m.command == 'RESUME']
        self.assertEqual(len(resume_messages), 2)
        self.assertEqual(resume_messages[0].params[0], 'TOKEN')
        new_new_token = resume_messages[0].params[1]
        self.assertNotEqual(token, new_new_token, 'should receive a new, strong resume token; instead got ' + new_new_token)
        self.assertNotEqual(new_token, new_new_token, 'should receive a new, strong resume token; instead got ' + new_new_token)
        # success message
        self.assertMessageEqual(resume_messages[1], command='RESUME', params=['SUCCESS', 'baz'])


    @cases.SpecificationSelector.requiredBySpecification('Oragono')
    def testBRB(self):
        self.connectClient('bar', capabilities=['batch', 'draft/labeled-response-0.2', 'message-tags', 'server-time', 'draft/resume-0.5'])
        ms = self.getMessages(1)
        self.joinChannel(1, '#xyz')

        welcome = self.connectClient('baz', capabilities=['batch', 'draft/labeled-response-0.2', 'server-time', 'draft/resume-0.5'])
        resume_messages = [m for m in welcome if m.command == 'RESUME']
        self.assertEqual(len(resume_messages), 1)
        self.assertEqual(resume_messages[0].params[0], 'TOKEN')
        token = resume_messages[0].params[1]
        self.joinChannel(2, '#xyz')

        self.getMessages(1)
        self.sendLine(2, 'BRB :software upgrade')
        # should receive, e.g., `BRB 210` (number of seconds)
        ms = [m for m in self.getMessages(2) if m.command == 'BRB']
        self.assertEqual(len(ms), 1)
        self.assertGreater(int(ms[0].params[0]), 1)
        # BRB disconnects you
        self.assertDisconnected(2)
        # without sending a QUIT line to friends
        self.assertEqual(self.getMessages(1), [])

        self.sendLine(1, 'PRIVMSG baz :hey there')
        # BRB message should be sent as an away message
        self.assertMessageEqual(self.getMessage(1), command=RPL_AWAY, params=['bar', 'baz', 'software upgrade'])

        self.addClient(3)
        self.sendLine(3, 'CAP REQ :batch account-tag message-tags draft/resume-0.5')
        self.sendLine(3, ' '.join(('RESUME', token, ANCIENT_TIMESTAMP)))
        ms = self.getMessages(3)

        resume_messages = [m for m in ms if m.command == 'RESUME']
        self.assertEqual(len(resume_messages), 2)
        self.assertEqual(resume_messages[0].params[0], 'TOKEN')
        self.assertMessageEqual(resume_messages[1], command='RESUME', params=['SUCCESS', 'baz'])

        privmsgs = [m for m in ms if m.command == 'PRIVMSG' and m.prefix.startswith('bar')]
        self.assertEqual(len(privmsgs), 1)
        self.assertMessageEqual(privmsgs[0], params=['baz', 'hey there'])

        # friend with the resume cap should receive a RESUMED message
        resumed_messages = [m for m in self.getMessages(1) if m.command == 'RESUMED']
        self.assertEqual(len(resumed_messages), 1)
        self.assertTrue(resumed_messages[0].prefix.startswith('baz'))
