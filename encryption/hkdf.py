from Crypto.Protocol.KDF import HKDF
from Crypto.Hash import SHA256


def derive_key(shared_secret, salt):
    return HKDF(shared_secret, key_len=32, salt=salt, hashmod=SHA256, context=b"chat-encryption")