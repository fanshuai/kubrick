from hashids import Hashids

from django.conf import settings


HID_MIN_LEN = 8

HID_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'

_pk_hashids = Hashids(
    salt=settings.HASHID_FIELD_SALT,
    min_length=HID_MIN_LEN,
    alphabet=HID_ALPHABET,
)


def pk_hashid_encode(pk: int):
    return _pk_hashids.encode(pk)


def pk_hashid_decode(pk: str):
    return _pk_hashids.decode(pk)[0]
