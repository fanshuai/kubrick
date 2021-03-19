"""
Token 转换及验证
"""
import logging
from typing import Optional
from django.core import signing
from django.conf import settings
from django.utils import baseconv

logger = logging.getLogger('django.debug')

key = signing.force_bytes(settings.SECRET_KEY)
signer = signing.TimestampSigner(b'token.switch' + key, salt='token.switch')


def token_dump(session_key: str) -> str:
    token = signer.sign(session_key)
    return token


def token_load(token: str, max_age=None) -> Optional[str]:
    try:
        session_key = signer.unsign(token, max_age=max_age)
    except (UnicodeError, signing.BadSignature) as exc:
        logger.warning(f'token_load__error {type(exc).__name__} {str(exc)}')
        return None
    return session_key


def token_load_ts(token: str) -> tuple:
    """ Token 验证及时间戳 """
    try:
        result = super(signer.__class__, signer).unsign(token)
        value, timestamp = result.rsplit(signer.sep, 1)
        timestamp = baseconv.base62.decode(timestamp)
    except (UnicodeError, signing.BadSignature) as exc:
        logger.warning(f'token_timestamp__error {type(exc).__name__} {str(exc)}')
        return None, None
    return value, timestamp
