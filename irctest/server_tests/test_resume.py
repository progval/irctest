"""
<https://github.com/DanielOaks/ircv3-specifications/blob/master+resume/extensions/resume.md>
"""

from irctest import cases


class ResumeTestCase(cases.BaseServerTestCase):

    @cases.SpecificationSelector.requiredBySpecification('Oragono')
    def testNoResumeByDefault(self):
        self.connectClient('bar', capabilities=['batch', 'echo-message', 'draft/labeled-response'])
        ms = self.getMessages(1)
        resume_messages = [m for m in ms if m.command == 'RESUME']
        self.assertEqual(resume_messages, [], 'should not see RESUME messages unless explicitly negotiated')

    @cases.SpecificationSelector.requiredBySpecification('Oragono')
    def testResume(self):
        self.connectClient('bar', capabilities=['batch', 'draft/labeled-response', 'server-time'])
        ms = self.getMessages(1)

        welcome = self.connectClient('baz', capabilities=['batch', 'draft/labeled-response', 'server-time', 'draft/resume-0.2'])
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
        self.sendLine(3, 'CAP REQ :batch draft/labeled-response server-time draft/resume-0.2')
        self.sendLine(3, 'NICK tempnick')
        self.sendLine(3, 'USER tempuser 0 * tempuser')
        self.sendLine(3, 'RESUME baz ' + bad_token + ' 2006-01-02T15:04:05.999Z')

        # resume with a bad token MUST fail
        ms = self.getMessages(3)
        resume_err_messages = [m for m in ms if m.command == 'RESUME' and m.params[0] == 'ERR']
        self.assertEqual(len(resume_err_messages), 1)
        # however, registration should proceed with the alternative nick
        self.sendLine(3, 'CAP END')
        welcome_msgs = [m for m in self.getMessages(3) if m.command == '001'] # RPL_WELCOME
        self.assertEqual(welcome_msgs[0].params[0], 'tempnick')

        self.addClient()
        self.sendLine(4, 'CAP LS')
        self.sendLine(4, 'CAP REQ :batch draft/labeled-response server-time draft/resume-0.2')
        self.sendLine(4, 'NICK tempnick_')
        self.sendLine(4, 'USER tempuser 0 * tempuser')
        # resume with a timestamp in the distant past
        self.sendLine(4, 'RESUME baz ' + token + ' 2006-01-02T15:04:05.999Z')
        # successful resume does not require CAP END:
        # https://github.com/ircv3/ircv3-specifications/pull/306/files#r255318883
        ms = self.getMessages(4)

        resume_messages = [m for m in ms if m.command == 'RESUME']
        self.assertEqual(len(resume_messages), 2)
        self.assertEqual(resume_messages[0].params[0], 'TOKEN')
        new_token = resume_messages[0].params[1]
        self.assertNotEqual(token, new_token, 'should receive a new, strong resume token; instead got ' + new_token)
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

        # original client should have been disconnected
        self.assertDisconnected(2)
        # new client should be receiving PRIVMSG sent to baz
        self.sendLine(1, 'PRIVMSG baz :hello again')
        self.getMessages(1)
        self.assertMessageEqual(self.getMessage(4), command='PRIVMSG', params=['baz', 'hello again'])
