"""
Python One-Time Password
https://pyotp.readthedocs.io/
"""
import pyotp
import base64
import hashlib

from kubrick.settings import SECRET_KEY


def pyotp_secret(key):
    """ OTP Secret """
    key_bytes = f'{key}:{SECRET_KEY}'.encode()
    secret = base64.b32encode(hashlib.md5(key_bytes).digest())[:16]
    return secret


def pyotp_hotp(key):
    """ HOTP """
    secret = pyotp_secret(key)
    otp = pyotp.HOTP(secret)
    return otp


def pyotp_totp(key):
    """ TOTP """
    secret = pyotp_secret(key)
    otp = pyotp.TOTP(secret)
    return otp
