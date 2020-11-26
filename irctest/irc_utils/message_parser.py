import re
import collections

from .junkdrawer import MultipleReplacer

# http://ircv3.net/specs/core/message-tags-3.2.html#escaping-values
TAG_ESCAPE = [
    ('\\', '\\\\'), # \ -> \\
    (' ', r'\s'),
    (';', r'\:'),
    ('\r', r'\r'),
    ('\n', r'\n'),
    ]
unescape_tag_value = MultipleReplacer(
        dict(map(lambda x:(x[1],x[0]), TAG_ESCAPE)))

# TODO: validate host
tag_key_validator = re.compile(r'\+?(\S+/)?[a-zA-Z0-9-]+')

def parse_tags(s):
    tags = {}
    for tag in s.split(';'):
        if '=' not in tag:
            tags[tag] = None
        else:
            (key, value) = tag.split('=', 1)
            assert tag_key_validator.match(key), \
                    'Invalid tag key: {}'.format(key)
            tags[key] = unescape_tag_value(value)
    return tags

Message = collections.namedtuple('Message',
        'tags prefix command params')

def parse_message(s):
    """Parse a message according to
    http://tools.ietf.org/html/rfc1459#section-2.3.1
    and
    http://ircv3.net/specs/core/message-tags-3.2.html"""
    s = s.rstrip('\r\n')
    if s.startswith('@'):
        (tags, s) = s.split(' ', 1)
        tags = parse_tags(tags[1:])
    else:
        tags = {}
    if ' :' in s:
        (other_tokens, trailing_param) = s.split(' :', 1)
        tokens = list(filter(bool, other_tokens.split(' '))) + [trailing_param]
    else:
        tokens = list(filter(bool, s.split(' ')))
    if tokens[0].startswith(':'):
        prefix = tokens.pop(0)[1:]
    else:
        prefix = None
    command = tokens.pop(0)
    params = tokens
    return Message(
            tags=tags,
            prefix=prefix,
            command=command,
            params=params,
            )
