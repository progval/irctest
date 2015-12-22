import enum

@enum.unique
class Specifications(enum.Enum):
    RFC1459 = 'RFC1459'
    RFC2812 = 'RFC2812'
    IRC301 = 'IRCv3.1'
    IRC302 = 'IRCv3.2'

    @classmethod
    def of_name(cls, name):
        name = name.upper()
        for spec in cls:
            if spec.value.upper() == name:
                return spec
        raise ValueError(name)
