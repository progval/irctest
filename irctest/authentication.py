import enum
import collections

@enum.unique
class Mechanisms(enum.Enum):
    @classmethod
    def as_string(cls, mech):
        return {cls.plain: 'PLAIN'}[mech]
    plain = 1

Authentication = collections.namedtuple('Authentication',
        'mechanisms username password certificate')
Authentication.__new__.__defaults__ = ([Mechanisms.plain], None, None, None)
