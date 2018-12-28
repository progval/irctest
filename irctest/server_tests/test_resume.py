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

        self.addClient()
        self.sendLine(3, 'CAP LS')
        self.sendLine(3, 'CAP REQ :batch draft/labeled-response server-time draft/resume-0.2')
        self.sendLine(3, 'NICK tempnick')
        self.sendLine(3, 'USER tempuser 0 * tempuser')
        # resume with a timestamp in the distant past
        self.sendLine(3, 'RESUME baz ' + token + ' 2006-01-02T15:04:05.999Z')
        self.sendLine(3, 'CAP END')
        ms = self.getMessages(3)

        resume_messages = [m for m in ms if m.command == 'RESUME']
        self.assertEqual(len(resume_messages), 2)
        self.assertEqual(resume_messages[0].params[0], 'TOKEN')
        new_token = resume_messages[0].params[1]
        self.assertNotEqual(token, new_token, 'should receive a new, strong resume token; instead got ' + new_token)
        self.assertMessageEqual(resume_messages[1], command='RESUME', params=['SUCCESS', 'baz'])

        # test replay of messages
        privmsgs = [m for m in ms if m.command == 'PRIVMSG']
        self.assertEqual(len(privmsgs), 2)
        privmsgs.sort(key=lambda m: m.params[0])
        self.assertMessageEqual(privmsgs[0], command='PRIVMSG', params=['#xyz', 'hello friends'])
        self.assertMessageEqual(privmsgs[1], command='PRIVMSG', params=['baz', 'hello friend singular'])
        # should replay with the original server-time
        # TODO this probably isn't testing anything because the timestamp only has second resolution,
        # hence will typically match by accident
        self.assertEqual(privmsgs[0].tags.get('time'), channelMsgTime)
