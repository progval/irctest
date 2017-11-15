import ecdsa
import base64
import pyxmpp2_scram as scram

from irctest import cases
from irctest import authentication
from irctest.irc_utils.message_parser import Message

ECDSA_KEY = """
-----BEGIN EC PARAMETERS-----
BggqhkjOPQMBBw==
-----END EC PARAMETERS-----
-----BEGIN EC PRIVATE KEY-----
MHcCAQEEIIJueQ3W2IrGbe9wKdOI75yGS7PYZSj6W4tg854hlsvmoAoGCCqGSM49
AwEHoUQDQgAEAZmaVhNSMmV5r8FXPvKuMnqDKyIA9pDHN5TNMfiF3mMeikGgK10W
IRX9cyi2wdYg9mUUYyh9GKdBCYHGUJAiCA==
-----END EC PRIVATE KEY-----
"""

class SaslTestCase(cases.BaseClientTestCase, cases.ClientNegociationHelper,
                   cases.OptionalityHelper):
    @cases.OptionalityHelper.skipUnlessHasMechanism('PLAIN')
    def testPlain(self):
        """Test PLAIN authentication with correct username/password."""
        auth = authentication.Authentication(
                mechanisms=[authentication.Mechanisms.plain],
                username='jilles',
                password='sesame',
                )
        m = self.negotiateCapabilities(['sasl'], auth=auth)
        self.assertEqual(m, Message([], None, 'AUTHENTICATE', ['PLAIN']))
        self.sendLine('AUTHENTICATE +')
        m = self.getMessage()
        self.assertEqual(m, Message([], None, 'AUTHENTICATE',
            ['amlsbGVzAGppbGxlcwBzZXNhbWU=']))
        self.sendLine('900 * * jilles :You are now logged in.')
        self.sendLine('903 * :SASL authentication successful')
        m = self.negotiateCapabilities(['sasl'], False)
        self.assertEqual(m, Message([], None, 'CAP', ['END']))

    @cases.OptionalityHelper.skipUnlessHasMechanism('PLAIN')
    def testPlainNotAvailable(self):
        """`sasl=EXTERNAL` is advertized, whereas the client is configured
        to use PLAIN.

        A client implementing sasl-3.2 can give up authentication immediately.
        A client not implementing it will try authenticating, and will get
        a 904.
        """
        auth = authentication.Authentication(
                mechanisms=[authentication.Mechanisms.plain],
                username='jilles',
                password='sesame',
                )
        m = self.negotiateCapabilities(['sasl=EXTERNAL'], auth=auth)
        self.assertEqual(self.acked_capabilities, {'sasl'})
        if m == Message([], None, 'CAP', ['END']):
            # IRCv3.2-style
            return
        self.assertEqual(m, Message([], None, 'AUTHENTICATE', ['PLAIN']))
        self.sendLine('904 {} :SASL auth failed'.format(self.nick))
        m = self.getMessage()
        self.assertMessageEqual(m, command='CAP')


    @cases.OptionalityHelper.skipUnlessHasMechanism('PLAIN')
    def testPlainLarge(self):
        """Test the client splits large AUTHENTICATE messages whose payload
        is not a multiple of 400.
        <http://ircv3.net/specs/extensions/sasl-3.1.html#the-authenticate-command>
        """
        # TODO: authzid is optional
        auth = authentication.Authentication(
                mechanisms=[authentication.Mechanisms.plain],
                username='foo',
                password='bar'*200,
                )
        authstring = base64.b64encode(b'\x00'.join(
            [b'foo', b'foo', b'bar'*200])).decode()
        m = self.negotiateCapabilities(['sasl'], auth=auth)
        self.assertEqual(m, Message([], None, 'AUTHENTICATE', ['PLAIN']))
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

    @cases.OptionalityHelper.skipUnlessHasMechanism('PLAIN')
    def testPlainLargeMultiple(self):
        """Test the client splits large AUTHENTICATE messages whose payload
        is a multiple of 400.
        <http://ircv3.net/specs/extensions/sasl-3.1.html#the-authenticate-command>
        """
        # TODO: authzid is optional
        auth = authentication.Authentication(
                mechanisms=[authentication.Mechanisms.plain],
                username='foo',
                password='quux'*148,
                )
        authstring = base64.b64encode(b'\x00'.join(
            [b'foo', b'foo', b'quux'*148])).decode()
        m = self.negotiateCapabilities(['sasl'], auth=auth)
        self.assertEqual(m, Message([], None, 'AUTHENTICATE', ['PLAIN']))
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

    @cases.OptionalityHelper.skipUnlessHasMechanism('ECDSA-NIST256P-CHALLENGE')
    def testEcdsa(self):
        """Test ECDSA authentication.
        """
        auth = authentication.Authentication(
                mechanisms=[authentication.Mechanisms.ecdsa_nist256p_challenge],
                username='jilles',
                ecdsa_key=ECDSA_KEY,
                )
        m = self.negotiateCapabilities(['sasl'], auth=auth)
        self.assertEqual(m, Message([], None, 'AUTHENTICATE', ['ECDSA-NIST256P-CHALLENGE']))
        self.sendLine('AUTHENTICATE +')
        m = self.getMessage()
        self.assertEqual(m, Message([], None, 'AUTHENTICATE',
            ['amlsbGVz'])) # jilles
        self.sendLine('AUTHENTICATE Zm9vYmFy') # foobar
        m = self.getMessage()
        self.assertMessageEqual(m, command='AUTHENTICATE')
        sk = ecdsa.SigningKey.from_pem(ECDSA_KEY)
        vk = sk.get_verifying_key()
        signature = base64.b64decode(m.params[0])
        try:
            vk.verify(signature, b'foobar')
        except ecdsa.BadSignatureError:
            raise AssertionError('Bad signature')
        self.sendLine('900 * * foo :You are now logged in.')
        self.sendLine('903 * :SASL authentication successful')
        m = self.negotiateCapabilities(['sasl'], False)
        self.assertEqual(m, Message([], None, 'CAP', ['END']))

    @cases.OptionalityHelper.skipUnlessHasMechanism('SCRAM-SHA-256')
    def testScram(self):
        """Test SCRAM-SHA-256 authentication.
        """
        auth = authentication.Authentication(
                mechanisms=[authentication.Mechanisms.scram_sha_256],
                username='jilles',
                password='sesame',
                )
        class PasswdDb:
            def get_password(self, *args):
                return ('sesame', 'plain')
        authenticator = scram.SCRAMServerAuthenticator('SHA-256',
                channel_binding=False, password_database=PasswdDb())

        m = self.negotiateCapabilities(['sasl'], auth=auth)
        self.assertEqual(m, Message([], None, 'AUTHENTICATE', ['SCRAM-SHA-256']))
        self.sendLine('AUTHENTICATE +')

        m = self.getMessage()
        self.assertEqual(m.command, 'AUTHENTICATE', m)
        client_first = base64.b64decode(m.params[0])
        response = authenticator.start(properties={}, initial_response=client_first)
        assert isinstance(response, bytes), response
        self.sendLine('AUTHENTICATE :' + base64.b64encode(response).decode())

        m = self.getMessage()
        self.assertEqual(m.command, 'AUTHENTICATE', m)
        msg = base64.b64decode(m.params[0])
        r = authenticator.response(msg)
        assert isinstance(r, tuple), r
        assert len(r) == 2, r
        (properties, response) = r
        self.sendLine('AUTHENTICATE :' + base64.b64encode(response).decode())
        self.assertEqual(properties, {'authzid': None, 'username': 'jilles'})

        m = self.getMessage()
        self.assertEqual(m.command, 'AUTHENTICATE', m)
        self.assertEqual(m.params, ['+'], m)

    @cases.OptionalityHelper.skipUnlessHasMechanism('SCRAM-SHA-256')
    def testScramBadPassword(self):
        """Test SCRAM-SHA-256 authentication with a bad password.
        """
        auth = authentication.Authentication(
                mechanisms=[authentication.Mechanisms.scram_sha_256],
                username='jilles',
                password='sesame',
                )
        class PasswdDb:
            def get_password(self, *args):
                return ('notsesame', 'plain')
        authenticator = scram.SCRAMServerAuthenticator('SHA-256',
                channel_binding=False, password_database=PasswdDb())

        m = self.negotiateCapabilities(['sasl'], auth=auth)
        self.assertEqual(m, Message([], None, 'AUTHENTICATE', ['SCRAM-SHA-256']))
        self.sendLine('AUTHENTICATE +')

        m = self.getMessage()
        self.assertEqual(m.command, 'AUTHENTICATE', m)
        client_first = base64.b64decode(m.params[0])
        response = authenticator.start(properties={}, initial_response=client_first)
        assert isinstance(response, bytes), response
        self.sendLine('AUTHENTICATE :' + base64.b64encode(response).decode())

        m = self.getMessage()
        self.assertEqual(m.command, 'AUTHENTICATE', m)
        msg = base64.b64decode(m.params[0])
        with self.assertRaises(scram.NotAuthorizedException):
            authenticator.response(msg)

class Irc302SaslTestCase(cases.BaseClientTestCase, cases.ClientNegociationHelper,
                         cases.OptionalityHelper):
    @cases.OptionalityHelper.skipUnlessHasMechanism('PLAIN')
    def testPlainNotAvailable(self):
        """Test the client does not try to authenticate using a mechanism the
        server does not advertise.
        Actually, this is optional."""
        auth = authentication.Authentication(
                mechanisms=[authentication.Mechanisms.plain],
                username='jilles',
                password='sesame',
                )
        m = self.negotiateCapabilities(['sasl=EXTERNAL'], auth=auth)
        self.assertEqual(self.acked_capabilities, {'sasl'})
        self.assertEqual(m, Message([], None, 'CAP', ['END']))
