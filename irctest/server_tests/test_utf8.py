from irctest import cases
from irctest.numerics import ERR_UNKNOWNERROR

class Utf8TestCase(cases.BaseServerTestCase, cases.OptionalityHelper):
    @cases.SpecificationSelector.requiredBySpecification('Oragono')
    def testUtf8Validation(self):
        self.connectClient('bar', capabilities=['batch', 'echo-message', 'labeled-response', 'message-tags'])
        self.joinChannel(1, '#qux')
        self.sendLine(1, 'PRIVMSG #qux hi')
        ms = self.getMessages(1)
        self.assertMessageEqual([m for m in ms if m.command == 'PRIVMSG'][0], params=['#qux', 'hi'])

        self.sendLine(1, b'PRIVMSG #qux hi\xaa')
        ms = self.getMessages(1)
        self.assertEqual(len(ms), 1)
        self.assertEqual(ms[0].command, ERR_UNKNOWNERROR)

        self.sendLine(1, b'@label=xyz PRIVMSG #qux hi\xaa')
        ms = self.getMessages(1)
        self.assertEqual(len(ms), 1)
        self.assertEqual(ms[0].command, ERR_UNKNOWNERROR)
        self.assertEqual(ms[0].tags.get('label'), 'xyz')
