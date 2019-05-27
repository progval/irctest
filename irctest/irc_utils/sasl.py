import base64

def sasl_plain_blob(username, passphrase):
    blob = base64.b64encode(b'\x00'.join((username.encode('utf-8'), username.encode('utf-8'), passphrase.encode('utf-8'))))
    blobstr = blob.decode('ascii')
    return f'AUTHENTICATE {blobstr}'
