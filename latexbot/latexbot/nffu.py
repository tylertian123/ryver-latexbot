"""
nffu functions.

See https://github.com/tylertian123/nffu.
"""

import hashlib
import hmac
import random


def generate_signup_code(hmac_secret: bytes, unix_time: int) -> str:
    """
    generate a signup code

    :param unix_time: should be in UTC
    """

    unix_minutes = unix_time // 60

    data = unix_minutes.to_bytes(8, byteorder='big', signed=False)
    mac  = hmac.new(hmac_secret, data, 'sha256').digest()
    i    = mac[-1] % 16
    trun = int.from_bytes(mac[i:i+4], byteorder='big', signed=False) % 2**31
    hexa = trun % 16**6

    digested = hashlib.sha256(hmac_secret).hexdigest()
    identifiers = [
        digested[i:i+3] for i in range(0, len(digested), 16)
    ]

    return random.choice(identifiers) + format(hexa, "06x")
