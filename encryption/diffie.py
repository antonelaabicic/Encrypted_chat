from Crypto.PublicKey import ECC

def generate_keypair():
    private = ECC.generate(curve="P-256")
    public = private.public_key()

    return private, public

def compute_shared(private, other_public):
    shared_point = private.d * other_public.pointQ
    return int(shared_point.x).to_bytes(32, "big" )