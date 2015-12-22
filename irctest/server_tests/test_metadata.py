"""
Tests METADATA features.
<http://ircv3.net/specs/core/metadata-3.2.html>
"""

from irctest import cases
from irctest.irc_utils.message_parser import Message

class MetadataTestCase(cases.BaseServerTestCase):
    valid_metadata_keys = {'valid_key1', 'valid_key2'}
    invalid_metadata_keys = {'invalid_key1', 'invalid_key2'}
    @cases.SpecificationSelector.requiredBySpecification('IRCv3.2')
    def testInIsupport(self):
        """“If METADATA is supported, it MUST be specified in RPL_ISUPPORT
        using the METADATA key.”
        -- <http://ircv3.net/specs/core/metadata-3.2.html>
        """
        self.addClient()
        self.sendLine(1, 'CAP LS 302')
        self.getCapLs(1)
        self.sendLine(1, 'USER foo foo foo :foo')
        self.sendLine(1, 'NICK foo')
        self.sendLine(1, 'CAP END')
        self.skipToWelcome(1)
        m = self.getMessage(1)
        while m.command != '005': # RPL_ISUPPORT
            m = self.getMessage(1)
        self.assertIn('METADATA', {x.split('=')[0] for x in m.params[1:-1]},
                fail_msg='{item} missing from RPL_ISUPPORT')
        self.getMessages(1)

    @cases.SpecificationSelector.requiredBySpecification('IRCv3.2')
    def testGetOneUnsetValid(self):
        """<http://ircv3.net/specs/core/metadata-3.2.html#metadata-get>
        """
        self.connectClient('foo')
        self.sendLine(1, 'METADATA * GET valid_key1')
        m = self.getMessage(1)
        self.assertMessageEqual(m, command='766', # ERR_NOMATCHINGKEY
                fail_msg='Did not reply with 766 (ERR_NOMATCHINGKEY) to a '
                'request to an unset valid METADATA key.')

    @cases.SpecificationSelector.requiredBySpecification('IRCv3.2')
    def testGetTwoUnsetValid(self):
        """“Multiple keys may be given. The response will be either RPL_KEYVALUE,
        ERR_KEYINVALID or ERR_NOMATCHINGKEY for every key in order.”
        -- <http://ircv3.net/specs/core/metadata-3.2.html#metadata-get>
        """
        self.connectClient('foo')
        self.sendLine(1, 'METADATA * GET valid_key1 valid_key2')
        m = self.getMessage(1)
        self.assertMessageEqual(m, command='766', # ERR_NOMATCHINGKEY
                fail_msg='Did not reply with 766 (ERR_NOMATCHINGKEY) to a '
                'request to two unset valid METADATA key: {msg}')
        self.assertEqual(m.params[1], 'valid_key1', m,
                fail_msg='Response to “METADATA * GET valid_key1 valid_key2” '
                'did not respond to valid_key1 first: {msg}')
        m = self.getMessage(1)
        self.assertMessageEqual(m, command='766', # ERR_NOMATCHINGKEY
                fail_msg='Did not reply with two 766 (ERR_NOMATCHINGKEY) to a '
                'request to two unset valid METADATA key: {msg}')
        self.assertEqual(m.params[1], 'valid_key2', m,
                fail_msg='Response to “METADATA * GET valid_key1 valid_key2” '
                'did not respond to valid_key2 as second response: {msg}')

    @cases.SpecificationSelector.requiredBySpecification('IRCv3.2')
    def testListNoSet(self):
        """“This subcommand MUST list all currently-set metadata keys along
        with their values. The response will be zero or more RPL_KEYVALUE
        events, following by RPL_METADATAEND event.”
        -- <http://ircv3.net/specs/core/metadata-3.2.html#metadata-list>
        """
        self.connectClient('foo')
        self.sendLine(1, 'METADATA * LIST')
        m = self.getMessage(1)
        self.assertMessageEqual(m, command='762', # RPL_METADATAEND
                fail_msg='Response to “METADATA * LIST” was not '
                '762 (RPL_METADATAEND) but: {msg}')

    @cases.SpecificationSelector.requiredBySpecification('IRCv3.2')
    def testListInvalidTarget(self):
        """“In case of invalid target RPL_METADATAEND MUST NOT be sent.”
        -- <http://ircv3.net/specs/core/metadata-3.2.html#metadata-list>
        """
        self.connectClient('foo')
        self.sendLine(1, 'METADATA foobar LIST')
        m = self.getMessage(1)
        self.assertMessageEqual(m, command='765', # ERR_TARGETINVALID
                fail_msg='Response to “METADATA <invalid target> LIST” was '
                'not 765 (ERR_TARGETINVALID) but: {msg}')
        commands = {m.command for m in self.getMessages(1)}
        self.assertNotIn('762', commands,
                fail_msg='Sent “METADATA <invalid target> LIST”, got 765 '
                '(ERR_TARGETINVALID), and then 762 (RPL_METADATAEND)')

    def assertSetValue(self, target, key, value, displayable_value=None):
        if displayable_value is None:
            displayable_value = value
        self.sendLine(1, 'METADATA {} SET {} :{}'.format(target, key, value))
        m = self.getMessage(1)
        self.assertMessageEqual(m, command='761', # RPL_KEYVALUE
                fail_msg='Did not reply with 761 (RPL_KEYVALUE) to a valid '
                '“METADATA * SET {} :{}”: {msg}',
                extra_format=(key, displayable_value,))
        self.assertEqual(m.params[1], 'valid_key1', m,
                fail_msg='Second param of 761 after setting “{expects}” to '
                '“{}” is not “{expects}”: {msg}.',
                extra_format=(displayable_value,))
        self.assertEqual(m.params[3], value, m,
                fail_msg='Fourth param of 761 after setting “{0}” to '
                '“{1}” is not “{1}”: {msg}.',
                extra_format=(key, displayable_value))
        m = self.getMessage(1)
        self.assertMessageEqual(m, command='762', # RPL_METADATAEND
                fail_msg='Did not send RPL_METADATAEND after setting '
                'a valid METADATA key.')
    def assertGetValue(self, target, key, value, displayable_value=None):
        self.sendLine(1, 'METADATA * GET {}'.format(key))
        m = self.getMessage(1)
        self.assertMessageEqual(m, command='761', # RPL_KEYVALUE
                fail_msg='Did not reply with 761 (RPL_KEYVALUE) to a valid '
                '“METADATA * GET” when the key is set is set: {msg}')
        self.assertEqual(m.params[1], key, m,
                fail_msg='Second param of 761 after getting “{expects}” '
                '(which is set) is not “{expects}”: {msg}.')
        self.assertEqual(m.params[3], value, m,
                fail_msg='Fourth param of 761 after getting “{0}” '
                '(which is set to “{1}”) is not ”{1}”: {msg}.',
                extra_format=(key, displayable_value))
    def assertSetGetValue(self, target, key, value, displayable_value=None):
        self.assertSetValue(target, key, value, displayable_value)
        self.assertGetValue(target, key, value, displayable_value)

    @cases.SpecificationSelector.requiredBySpecification('IRCv3.2')
    def testSetGetValid(self):
        """<http://ircv3.net/specs/core/metadata-3.2.html>
        """
        self.connectClient('foo')
        self.assertSetGetValue('*', 'valid_key1', 'myvalue')

    @cases.SpecificationSelector.requiredBySpecification('IRCv3.2')
    def testSetGetZeroCharInValue(self):
        """“Values are unrestricted, except that they MUST be UTF-8.”
        -- <http://ircv3.net/specs/core/metadata-3.2.html#metadata-restrictions>
        """
        self.connectClient('foo')
        self.assertSetGetValue('*', 'valid_key1', 'zero->\0<-zero',
                'zero->\\0<-zero')

    @cases.SpecificationSelector.requiredBySpecification('IRCv3.2')
    def testSetGetHeartInValue(self):
        """“Values are unrestricted, except that they MUST be UTF-8.”
        -- <http://ircv3.net/specs/core/metadata-3.2.html#metadata-restrictions>
        """
        heart = b'\xf0\x9f\x92\x9c'.decode()
        self.connectClient('foo')
        self.assertSetGetValue('*', 'valid_key1', '->{}<-'.format(heart),
                'zero->{}<-zero'.format(heart.encode()))

    @cases.SpecificationSelector.requiredBySpecification('IRCv3.2')
    def testSetInvalidUtf8(self):
        """“Values are unrestricted, except that they MUST be UTF-8.”
        -- <http://ircv3.net/specs/core/metadata-3.2.html#metadata-restrictions>
        """
        self.connectClient('foo')
        # Sending directly because it is not valid UTF-8 so Python would
        # not like it
        self.clients[1].conn.sendall(b'METADATA * SET valid_key1 '
                b':invalid UTF-8 ->\xc3<-\r\n')
        commands = {m.command for m in self.getMessages(1)}
        self.assertNotIn('761', commands, # RPL_KEYVALUE
                fail_msg='Setting METADATA key to a value containing invalid '
                'UTF-8 was answered with 761 (RPL_KEYVALUE)')
        self.clients[1].conn.sendall(b'METADATA * SET valid_key1 '
                b':invalid UTF-8: \xc3\r\n')
        commands = {m.command for m in self.getMessages(1)}
        self.assertNotIn('761', commands, # RPL_KEYVALUE
                fail_msg='Setting METADATA key to a value containing invalid '
                'UTF-8 was answered with 761 (RPL_KEYVALUE)')
