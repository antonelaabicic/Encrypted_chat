from Crypto.Cipher import AES


def encrypt(key, plaintext, counter):
    cipher = AES.new(key, AES.MODE_GCM)

    nonce = cipher.nonce
    counter_bytes = counter.to_bytes(8, "big")

    cipher.update(counter_bytes)

    ciphertext, tag = cipher.encrypt_and_digest(plaintext.encode())

    return nonce + counter_bytes + ciphertext + tag

def decrypt(key, payload, last_counter):
    nonce = payload[:16]
    counter_bytes = payload[16:24]
    tag = payload[-16:]
    ciphertext = payload[24:-16]

    cipher = AES.new(key, AES.MODE_GCM, nonce=nonce)

    cipher.update(counter_bytes)  

    plaintext = cipher.decrypt_and_verify(ciphertext, tag)

    counter = int.from_bytes(counter_bytes, "big")

    if counter <= last_counter:
        raise Exception("Replay attack detected.")

    return plaintext.decode(), counter