import uuid

def default_nonce_factory():
    """Generate a random string for digest authentication challenges.
    The string should be cryptographicaly secure random pattern.
    :return: the string generated.
    :returntype: `bytes`
    """
    return uuid.uuid4().hex.encode("us-ascii")
