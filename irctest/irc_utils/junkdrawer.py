import datetime
from collections import namedtuple

HistoryMessage = namedtuple('HistoryMessage', ['time', 'msgid', 'target', 'text'])

def to_history_message(msg):
    return HistoryMessage(time=msg.tags.get('time'), msgid=msg.tags.get('msgid'), target=msg.params[0], text=msg.params[1])

# thanks jess!
IRCV3_FORMAT_STRFTIME = "%Y-%m-%dT%H:%M:%S.%f%z"

def ircv3_timestamp_to_unixtime(timestamp):
    return datetime.datetime.strptime(timestamp, IRCV3_FORMAT_STRFTIME).timestamp()
