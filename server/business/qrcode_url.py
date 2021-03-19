import logging
from django.urls import reverse
from django.http import QueryDict
from urllib.parse import urlparse, urlunparse, unquote

from kubrick.settings import SECRET_KEY
from kubrick.initialize import QRIMG_HOST
from server.corelib.sequence.idshift import hmac_hash

logger = logging.getLogger('kubrick.debug')


def get_unquote_url(quote_url):
    """ 编码URL解码 """
    url = unquote(quote_url)
    return url


def get_qrcode_uri(name, hotp, key):
    """ 获取用户码、场景码URI """
    kwargs = dict(hotp=hotp, key=key)
    assert name in ['page_qrimg_user', 'page_qrimg_symbol'], name
    path = reverse(name, kwargs=kwargs)
    url = f'{QRIMG_HOST}{path}'
    return url


def qrurl_with_sign(url):
    """ 获取Path签名URL """
    (scheme, netloc, path, params, query, fragment) = urlparse(url)
    query_dic = QueryDict(query).copy()
    full_path = scheme + '://' + netloc + path
    query_dic['sign'] = hmac_hash(SECRET_KEY, full_path)
    new_query = query_dic.urlencode()
    new_url = urlunparse((scheme, netloc, path, params, new_query, fragment))
    return new_url


def check_qrurl_sign(url):
    """ 检查Path签名URL """
    (scheme, netloc, path, params, query, fragment) = urlparse(url)
    query_dic = QueryDict(query).copy()
    full_path = scheme + '://' + netloc + path
    sign = hmac_hash(SECRET_KEY, full_path)
    is_ok = sign == query_dic.get('sign')
    return is_ok
