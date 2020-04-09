import secrets

def random_name(base):
    return base + '-' + secrets.token_hex(8)
