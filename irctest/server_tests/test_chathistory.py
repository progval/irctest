import secrets
import time
from collections import namedtuple

from irctest import cases

#ANCIENT_TIMESTAMP = '2006-01-02T15:04:05.999Z'

CHATHISTORY_CAP = 'draft/chathistory'
EVENT_PLAYBACK_CAP = 'draft/event-playback'

HistoryMessage = namedtuple('HistoryMessage', ['time', 'msgid', 'target', 'text'])

MYSQL_PASSWORD = ""

def to_history_message(msg):
    return HistoryMessage(time=msg.tags.get('time'), msgid=msg.tags.get('msgid'), target=msg.params[0], text=msg.params[1])

def validate_chathistory_batch(msgs):
    batch_tag = None
    closed_batch_tag = None
    result = []
    for msg in msgs:
        if msg.command == "BATCH":
            batch_param = msg.params[0]
            if batch_tag is None and batch_param[0] == '+':
                batch_tag = batch_param[1:]
            elif batch_param[0] == '-':
                closed_batch_tag = batch_param[1:]
        elif msg.command == "PRIVMSG" and batch_tag is not None and msg.tags.get("batch") == batch_tag:
            result.append(to_history_message(msg))
    assert batch_tag == closed_batch_tag
    return result

class ChathistoryTestCase(cases.BaseServerTestCase):

    def validate_echo_messages(self, num_messages, echo_messages):
        # sanity checks: should have received the correct number of echo messages,
        # all with distinct time tags (because we slept) and msgids
        self.assertEqual(len(echo_messages), num_messages)
        self.assertEqual(len(set(msg.msgid for msg in echo_messages)), num_messages)
        self.assertEqual(len(set(msg.time for msg in echo_messages)), num_messages)

    @cases.SpecificationSelector.requiredBySpecification('Oragono')
    def testChathistory(self):
        self.connectClient('bar', capabilities=['message-tags', 'server-time', 'echo-message', 'batch', 'labeled-response', CHATHISTORY_CAP, EVENT_PLAYBACK_CAP])
        chname = '#' + secrets.token_hex(12)
        self.joinChannel(1, chname)
        self.getMessages(1)

        NUM_MESSAGES = 10
        echo_messages = []
        for i in range(NUM_MESSAGES):
            self.sendLine(1, 'PRIVMSG %s :this is message %d' % (chname, i))
            echo_messages.extend(to_history_message(msg) for msg in self.getMessages(1))
            time.sleep(0.002)

        self.validate_echo_messages(NUM_MESSAGES, echo_messages)
        self.validate_chathistory(echo_messages, 1, chname)

    def customizedConfig(self):
        if MYSQL_PASSWORD == "":
            return None

        # enable mysql-backed history for all channels and logged-in clients
        config = self.controller.baseConfig()
        config['datastore']['mysql'] = {
           "enabled": True,
           "host": "localhost",
           "user": "oragono",
           "password": MYSQL_PASSWORD,
           "history-database": "oragono_history",
        }
        config['history']['persistent'] = {
            "enabled": True,
            "unregistered-channels": True,
            "registered-channels": "opt-out",
            "clients": "opt-out",
        }
        return config

    @cases.SpecificationSelector.requiredBySpecification('Oragono')
    def testChathistoryDMs(self):
        c1 = secrets.token_hex(12)
        c2 = secrets.token_hex(12)
        self.controller.registerUser(self, c1, c1)
        self.controller.registerUser(self, c2, c2)
        self.connectClient(c1, capabilities=['message-tags', 'server-time', 'echo-message', 'batch', 'labeled-response', CHATHISTORY_CAP, EVENT_PLAYBACK_CAP], password=c1)
        self.connectClient(c2, capabilities=['message-tags', 'server-time', 'echo-message', 'batch', 'labeled-response', CHATHISTORY_CAP, EVENT_PLAYBACK_CAP], password=c2)
        self.getMessages(1)
        self.getMessages(2)

        NUM_MESSAGES = 10
        echo_messages = []
        for i in range(NUM_MESSAGES):
            user = (i % 2) + 1
            if user == 1:
                target = c2
            else:
                target = c1
            self.getMessages(user)
            self.sendLine(user, 'PRIVMSG %s :this is message %d' % (target, i))
            echo_messages.extend(to_history_message(msg) for msg in self.getMessages(user))
            time.sleep(0.002)

        self.validate_echo_messages(NUM_MESSAGES, echo_messages)
        self.validate_chathistory(echo_messages, 1, c2)
        self.validate_chathistory(echo_messages, 1, '*')
        self.validate_chathistory(echo_messages, 2, c1)
        self.validate_chathistory(echo_messages, 2, '*')

        c3 = secrets.token_hex(12)
        self.controller.registerUser(self, c3, c3)
        self.connectClient(c3, capabilities=['message-tags', 'server-time', 'echo-message', 'batch', 'labeled-response', CHATHISTORY_CAP, EVENT_PLAYBACK_CAP], password=c3)
        self.sendLine(1, 'PRIVMSG %s :this is a message in a separate conversation' % (c3,))
        self.getMessages(1)
        self.sendLine(3, 'PRIVMSG %s :i agree that this is a separate conversation' % (c1,))
        self.getMessages(3)

        # additional messages with c3 should not show up in the c1-c2 history:
        self.validate_chathistory(echo_messages, 1, c2)
        self.validate_chathistory(echo_messages, 2, c1)

    def validate_chathistory(self, echo_messages, user, chname):
        INCLUSIVE_LIMIT = len(echo_messages) * 2

        self.sendLine(user, "CHATHISTORY LATEST %s * %d" % (chname, INCLUSIVE_LIMIT))
        result = validate_chathistory_batch(self.getMessages(user))
        self.assertEqual(echo_messages, result)

        self.sendLine(user, "CHATHISTORY LATEST %s * %d" % (chname, 5))
        result = validate_chathistory_batch(self.getMessages(user))
        self.assertEqual(echo_messages[-5:], result)

        self.sendLine(user, "CHATHISTORY LATEST %s * %d" % (chname, 1))
        result = validate_chathistory_batch(self.getMessages(user))
        self.assertEqual(echo_messages[-1:], result)

        self.sendLine(user, "CHATHISTORY LATEST %s msgid=%s %d" % (chname, echo_messages[4].msgid, INCLUSIVE_LIMIT))
        result = validate_chathistory_batch(self.getMessages(user))
        self.assertEqual(echo_messages[5:], result)

        self.sendLine(user, "CHATHISTORY LATEST %s timestamp=%s %d" % (chname, echo_messages[4].time, INCLUSIVE_LIMIT))
        result = validate_chathistory_batch(self.getMessages(user))
        self.assertEqual(echo_messages[5:], result)

        self.sendLine(user, "CHATHISTORY BEFORE %s msgid=%s %d" % (chname, echo_messages[6].msgid, INCLUSIVE_LIMIT))
        result = validate_chathistory_batch(self.getMessages(user))
        self.assertEqual(echo_messages[:6], result)

        self.sendLine(user, "CHATHISTORY BEFORE %s timestamp=%s %d" % (chname, echo_messages[6].time, INCLUSIVE_LIMIT))
        result = validate_chathistory_batch(self.getMessages(user))
        self.assertEqual(echo_messages[:6], result)

        self.sendLine(user, "CHATHISTORY BEFORE %s timestamp=%s %d" % (chname, echo_messages[6].time, 2))
        result = validate_chathistory_batch(self.getMessages(user))
        self.assertEqual(echo_messages[4:6], result)

        self.sendLine(user, "CHATHISTORY AFTER %s msgid=%s %d" % (chname, echo_messages[3].msgid, INCLUSIVE_LIMIT))
        result = validate_chathistory_batch(self.getMessages(user))
        self.assertEqual(echo_messages[4:], result)

        self.sendLine(user, "CHATHISTORY AFTER %s timestamp=%s %d" % (chname, echo_messages[3].time, INCLUSIVE_LIMIT))
        result = validate_chathistory_batch(self.getMessages(user))
        self.assertEqual(echo_messages[4:], result)

        self.sendLine(user, "CHATHISTORY AFTER %s timestamp=%s %d" % (chname, echo_messages[3].time, 3))
        result = validate_chathistory_batch(self.getMessages(user))
        self.assertEqual(echo_messages[4:7], result)

        # BETWEEN forwards and backwards
        self.sendLine(user, "CHATHISTORY BETWEEN %s msgid=%s msgid=%s %d" % (chname, echo_messages[0].msgid, echo_messages[-1].msgid, INCLUSIVE_LIMIT))
        result = validate_chathistory_batch(self.getMessages(user))
        self.assertEqual(echo_messages[1:-1], result)

        self.sendLine(user, "CHATHISTORY BETWEEN %s msgid=%s msgid=%s %d" % (chname, echo_messages[-1].msgid, echo_messages[0].msgid, INCLUSIVE_LIMIT))
        result = validate_chathistory_batch(self.getMessages(user))
        self.assertEqual(echo_messages[1:-1], result)

        # BETWEEN forwards and backwards with a limit, should get different results this time
        self.sendLine(user, "CHATHISTORY BETWEEN %s msgid=%s msgid=%s %d" % (chname, echo_messages[0].msgid, echo_messages[-1].msgid, 3))
        result = validate_chathistory_batch(self.getMessages(user))
        self.assertEqual(echo_messages[1:4], result)

        self.sendLine(user, "CHATHISTORY BETWEEN %s msgid=%s msgid=%s %d" % (chname, echo_messages[-1].msgid, echo_messages[0].msgid, 3))
        result = validate_chathistory_batch(self.getMessages(user))
        self.assertEqual(echo_messages[-4:-1], result)

        # same stuff again but with timestamps
        self.sendLine(user, "CHATHISTORY BETWEEN %s timestamp=%s timestamp=%s %d" % (chname, echo_messages[0].time, echo_messages[-1].time, INCLUSIVE_LIMIT))
        result = validate_chathistory_batch(self.getMessages(user))
        self.assertEqual(echo_messages[1:-1], result)
        self.sendLine(user, "CHATHISTORY BETWEEN %s timestamp=%s timestamp=%s %d" % (chname, echo_messages[-1].time, echo_messages[0].time, INCLUSIVE_LIMIT))
        result = validate_chathistory_batch(self.getMessages(user))
        self.assertEqual(echo_messages[1:-1], result)
        self.sendLine(user, "CHATHISTORY BETWEEN %s timestamp=%s timestamp=%s %d" % (chname, echo_messages[0].time, echo_messages[-1].time, 3))
        result = validate_chathistory_batch(self.getMessages(user))
        self.assertEqual(echo_messages[1:4], result)
        self.sendLine(user, "CHATHISTORY BETWEEN %s timestamp=%s timestamp=%s %d" % (chname, echo_messages[-1].time, echo_messages[0].time, 3))
        result = validate_chathistory_batch(self.getMessages(user))
        self.assertEqual(echo_messages[-4:-1], result)

        # AROUND
        self.sendLine(user, "CHATHISTORY AROUND %s msgid=%s %d" % (chname, echo_messages[7].msgid, 1))
        result = validate_chathistory_batch(self.getMessages(user))
        self.assertEqual([echo_messages[7]], result)

        self.sendLine(user, "CHATHISTORY AROUND %s msgid=%s %d" % (chname, echo_messages[7].msgid, 3))
        result = validate_chathistory_batch(self.getMessages(user))
        self.assertEqual(echo_messages[6:9], result)

        self.sendLine(user, "CHATHISTORY AROUND %s timestamp=%s %d" % (chname, echo_messages[7].time, 3))
        result = validate_chathistory_batch(self.getMessages(user))
        self.assertIn(echo_messages[7], result)
