import base64
from irctest import cases
from irctest import authentication
from irctest.irc_utils.message_parser import Message

class CapTestCase(cases.BaseClientTestCase, cases.ClientNegociationHelper):
    def testPlain(self):
        auth = authentication.Authentication(
                mechanisms=[authentication.Mechanisms.plain],
                username='jilles',
                password='sesame',
                )
        m = self.negotiateCapabilities(['sasl'], auth=auth)
        self.assertEqual(m.command, 'AUTHENTICATE', m)
        self.sendLine('AUTHENTICATE +')
        m = self.getMessage()
        self.assertEqual(m, Message([], None, 'AUTHENTICATE',
            ['amlsbGVzAGppbGxlcwBzZXNhbWU=']))
        self.sendLine('900 * * jilles :You are now logged in.')
        self.sendLine('903 * :SASL authentication successful')
        m = self.negotiateCapabilities(['sasl'], False)
        self.assertEqual(m, Message([], None, 'CAP', ['END']))

    def testPlainLarge(self):
        # TODO: authzid is optional
        auth = authentication.Authentication(
                mechanisms=[authentication.Mechanisms.plain],
                username='foo',
                password='bar'*200,
                )
        authstring = base64.b64encode(b'\x00'.join(
            [b'foo', b'foo', b'bar'*200])).decode()
        m = self.negotiateCapabilities(['sasl'], auth=auth)
        self.assertEqual(m.command, 'AUTHENTICATE', m)
        self.sendLine('AUTHENTICATE +')
        m = self.getMessage()
        self.assertEqual(m, Message([], None, 'AUTHENTICATE',
            [authstring[0:400]]), m)
        m = self.getMessage()
        self.assertEqual(m, Message([], None, 'AUTHENTICATE',
            [authstring[400:800]]))
        m = self.getMessage()
        self.assertEqual(m, Message([], None, 'AUTHENTICATE',
            [authstring[800:]]))
        self.sendLine('900 * * {} :You are now logged in.'.format('foo'))
        self.sendLine('903 * :SASL authentication successful')
        m = self.negotiateCapabilities(['sasl'], False)
        self.assertEqual(m, Message([], None, 'CAP', ['END']))

    def testPlainLargeMultiple(self):
        # TODO: authzid is optional
        auth = authentication.Authentication(
                mechanisms=[authentication.Mechanisms.plain],
                username='foo',
                password='quux'*148,
                )
        authstring = base64.b64encode(b'\x00'.join(
            [b'foo', b'foo', b'quux'*148])).decode()
        m = self.negotiateCapabilities(['sasl'], auth=auth)
        self.assertEqual(m.command, 'AUTHENTICATE', m)
        self.sendLine('AUTHENTICATE +')
        m = self.getMessage()
        self.assertEqual(m, Message([], None, 'AUTHENTICATE',
            [authstring[0:400]]), m)
        m = self.getMessage()
        self.assertEqual(m, Message([], None, 'AUTHENTICATE',
            [authstring[400:800]]))
        m = self.getMessage()
        self.assertEqual(m, Message([], None, 'AUTHENTICATE',
            ['+']))
        self.sendLine('900 * * {} :You are now logged in.'.format('foo'))
        self.sendLine('903 * :SASL authentication successful')
        m = self.negotiateCapabilities(['sasl'], False)
        self.assertEqual(m, Message([], None, 'CAP', ['END']))
