class ScramException(Exception):
    pass

class BadChallengeException(ScramException):
    pass

class ExtraChallengeException(ScramException):
    pass

class ServerScramError(ScramException):
    pass

class BadSuccessException(ScramException):
    pass

class NotAuthorizedException(ScramException):
    pass
