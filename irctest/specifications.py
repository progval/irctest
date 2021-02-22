import enum


@enum.unique
class Specifications(enum.Enum):
    RFC1459 = "RFC1459"
    RFC2812 = "RFC2812"
    RFCDeprecated = "RFC-deprecated"
    IRC301 = "IRCv3.1"
    IRC302 = "IRCv3.2"
    IRC302Deprecated = "IRCv3.2-deprecated"
    Oragono = "Oragono"
    Multiline = "multiline"
    MessageTags = "message-tags"

    @classmethod
    def of_name(cls, name):
        name = name.upper()
        for spec in cls:
            if spec.value.upper() == name:
                return spec
        raise ValueError(name)
