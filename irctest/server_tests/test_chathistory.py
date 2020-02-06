import secrets
import time
from collections import namedtuple

from irctest import cases

#ANCIENT_TIMESTAMP = '2006-01-02T15:04:05.999Z'

CHATHISTORY_CAP = 'draft/chathistory'
EVENT_PLAYBACK_CAP = 'draft/event-playback'

HistoryMessage = namedtuple('HistoryMessage', ['time', 'msgid', 'text'])

def to_history_message(msg):
    return HistoryMessage(time=msg.tags.get('time'), msgid=msg.tags.get('msgid'), text=msg.params[1])

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

    @cases.SpecificationSelector.requiredBySpecification('Oragono')
    def testChathistory(self):
        self.connectClient('bar', capabilities=['message-tags', 'server-time', 'echo-message', 'batch', 'labeled-response', CHATHISTORY_CAP, EVENT_PLAYBACK_CAP])
        chname = '#' + secrets.token_hex(12)
        self.joinChannel(1, chname)
        self.getMessages(1)

        NUM_MESSAGES = 10
        INCLUSIVE_LIMIT = NUM_MESSAGES * 2
        echo_messages = []
        for i in range(NUM_MESSAGES):
            self.sendLine(1, 'PRIVMSG %s :this is message %d' % (chname, i))
            echo_messages.extend(to_history_message(msg) for msg in self.getMessages(1))
            time.sleep(0.002)
        # sanity checks: should have received the correct number of echo messages,
        # all with distinct time tags (because we slept) and msgids
        self.assertEqual(len(echo_messages), NUM_MESSAGES)
        self.assertEqual(len(set(msg.msgid for msg in echo_messages)), NUM_MESSAGES)
        self.assertEqual(len(set(msg.time for msg in echo_messages)), NUM_MESSAGES)

        self.sendLine(1, "CHATHISTORY LATEST %s * %d" % (chname, INCLUSIVE_LIMIT))
        result = validate_chathistory_batch(self.getMessages(1))
        self.assertEqual(echo_messages, result)

        self.sendLine(1, "CHATHISTORY LATEST %s * %d" % (chname, 5))
        result = validate_chathistory_batch(self.getMessages(1))
        self.assertEqual(echo_messages[-5:], result)

        self.sendLine(1, "CHATHISTORY LATEST %s * %d" % (chname, 1))
        result = validate_chathistory_batch(self.getMessages(1))
        self.assertEqual(echo_messages[-1:], result)

        self.sendLine(1, "CHATHISTORY LATEST %s msgid=%s %d" % (chname, echo_messages[4].msgid, INCLUSIVE_LIMIT))
        result = validate_chathistory_batch(self.getMessages(1))
        self.assertEqual(echo_messages[5:], result)

        self.sendLine(1, "CHATHISTORY LATEST %s timestamp=%s %d" % (chname, echo_messages[4].time, INCLUSIVE_LIMIT))
        result = validate_chathistory_batch(self.getMessages(1))
        self.assertEqual(echo_messages[5:], result)

        self.sendLine(1, "CHATHISTORY BEFORE %s msgid=%s %d" % (chname, echo_messages[6].msgid, INCLUSIVE_LIMIT))
        result = validate_chathistory_batch(self.getMessages(1))
        self.assertEqual(echo_messages[:6], result)

        self.sendLine(1, "CHATHISTORY BEFORE %s timestamp=%s %d" % (chname, echo_messages[6].time, INCLUSIVE_LIMIT))
        result = validate_chathistory_batch(self.getMessages(1))
        self.assertEqual(echo_messages[:6], result)

        self.sendLine(1, "CHATHISTORY BEFORE %s timestamp=%s %d" % (chname, echo_messages[6].time, 2))
        result = validate_chathistory_batch(self.getMessages(1))
        self.assertEqual(echo_messages[4:6], result)

        self.sendLine(1, "CHATHISTORY AFTER %s msgid=%s %d" % (chname, echo_messages[3].msgid, INCLUSIVE_LIMIT))
        result = validate_chathistory_batch(self.getMessages(1))
        self.assertEqual(echo_messages[4:], result)

        self.sendLine(1, "CHATHISTORY AFTER %s timestamp=%s %d" % (chname, echo_messages[3].time, INCLUSIVE_LIMIT))
        result = validate_chathistory_batch(self.getMessages(1))
        self.assertEqual(echo_messages[4:], result)

        self.sendLine(1, "CHATHISTORY AFTER %s timestamp=%s %d" % (chname, echo_messages[3].time, 3))
        result = validate_chathistory_batch(self.getMessages(1))
        self.assertEqual(echo_messages[4:7], result)

        # BETWEEN forwards and backwards
        self.sendLine(1, "CHATHISTORY BETWEEN %s msgid=%s msgid=%s %d" % (chname, echo_messages[0].msgid, echo_messages[-1].msgid, INCLUSIVE_LIMIT))
        result = validate_chathistory_batch(self.getMessages(1))
        self.assertEqual(echo_messages[1:-1], result)

        self.sendLine(1, "CHATHISTORY BETWEEN %s msgid=%s msgid=%s %d" % (chname, echo_messages[-1].msgid, echo_messages[0].msgid, INCLUSIVE_LIMIT))
        result = validate_chathistory_batch(self.getMessages(1))
        self.assertEqual(echo_messages[1:-1], result)

        # BETWEEN forwards and backwards with a limit, should get different results this time
        self.sendLine(1, "CHATHISTORY BETWEEN %s msgid=%s msgid=%s %d" % (chname, echo_messages[0].msgid, echo_messages[-1].msgid, 3))
        result = validate_chathistory_batch(self.getMessages(1))
        self.assertEqual(echo_messages[1:4], result)

        self.sendLine(1, "CHATHISTORY BETWEEN %s msgid=%s msgid=%s %d" % (chname, echo_messages[-1].msgid, echo_messages[0].msgid, 3))
        result = validate_chathistory_batch(self.getMessages(1))
        self.assertEqual(echo_messages[-4:-1], result)

        # same stuff again but with timestamps
        self.sendLine(1, "CHATHISTORY BETWEEN %s timestamp=%s timestamp=%s %d" % (chname, echo_messages[0].time, echo_messages[-1].time, INCLUSIVE_LIMIT))
        result = validate_chathistory_batch(self.getMessages(1))
        self.assertEqual(echo_messages[1:-1], result)
        self.sendLine(1, "CHATHISTORY BETWEEN %s timestamp=%s timestamp=%s %d" % (chname, echo_messages[-1].time, echo_messages[0].time, INCLUSIVE_LIMIT))
        result = validate_chathistory_batch(self.getMessages(1))
        self.assertEqual(echo_messages[1:-1], result)
        self.sendLine(1, "CHATHISTORY BETWEEN %s timestamp=%s timestamp=%s %d" % (chname, echo_messages[0].time, echo_messages[-1].time, 3))
        result = validate_chathistory_batch(self.getMessages(1))
        self.assertEqual(echo_messages[1:4], result)
        self.sendLine(1, "CHATHISTORY BETWEEN %s timestamp=%s timestamp=%s %d" % (chname, echo_messages[-1].time, echo_messages[0].time, 3))
        result = validate_chathistory_batch(self.getMessages(1))
        self.assertEqual(echo_messages[-4:-1], result)

        # AROUND
        self.sendLine(1, "CHATHISTORY AROUND %s msgid=%s %d" % (chname, echo_messages[7].msgid, 1))
        result = validate_chathistory_batch(self.getMessages(1))
        self.assertEqual([echo_messages[7]], result)

        self.sendLine(1, "CHATHISTORY AROUND %s msgid=%s %d" % (chname, echo_messages[7].msgid, 3))
        result = validate_chathistory_batch(self.getMessages(1))
        self.assertEqual(echo_messages[6:9], result)

        self.sendLine(1, "CHATHISTORY AROUND %s timestamp=%s %d" % (chname, echo_messages[7].time, 3))
        result = validate_chathistory_batch(self.getMessages(1))
        self.assertIn(echo_messages[7], result)
