"""
通过API服务访问二维码路径，MOCK View来解析路径参数
"""
import time
import logging
from django.urls import reverse
from django.http import Http404
from django.core.cache import cache
from django.views.decorators.cache import cache_page
from django.views.generic.base import RedirectView, TemplateView

from kubrick.settings import SECRET_KEY
from kubrick.initialize import QRIMG_HOST
from server.applibs.release.models import Symbol
from server.applibs.account.models import UserCode
from server.business.qrcode_url import check_qrurl_sign
from server.corelib.sequence import idshift

logger = logging.getLogger('kubrick.debug')


not_found_url = 'not-found'


def url_timed_hash_redirect(url):
    """
    二维码解析，按时间求Hash，缓存后重定向
    每一千秒(约一刻钟)更新一次
    :param url: 二维码原始路径
    :return: Hash值、缓存Key、重定向新Url
    """
    key = str(int(time.time()) // 1000)
    key = f'{SECRET_KEY}:{key}'
    hashed = idshift.hmac_hash(key, url)
    cache_key = f'qrimgurlhash:{hashed}'
    redirect = reverse('qrimg_view', kwargs=dict(hashed=hashed))
    return cache_key, redirect


class QRIMGMockRedirectView(RedirectView):
    """ 二维码内容，用来URL生成和解析，具体访问在QRImage[qr.ifand.com] """

    permanent = False
    query_string = True

    def get_redirect_url(self, *args, **kwargs):
        path = self.request.path
        url = '{host}/{key}-{hotp}'.format(host=QRIMG_HOST, **kwargs)
        logger.warning(f'QRIMGMockRedirectView__mock {path}: {url}')
        args = self.request.META.get('QUERY_STRING', '')
        if args and self.query_string:
            url = f'{url}?{args}'
        return url


class QRResolveUserView(RedirectView):
    """ 用户码页面解析 """

    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        url = self.request.build_absolute_uri()
        cache_key, redirect = url_timed_hash_redirect(url)
        if cache.ttl(cache_key) > 100:
            return redirect
        if not check_qrurl_sign(url):
            logger.warning(f'QRResolveUserView.check_qrurl_sign__fail {url}')
            return not_found_url
        try:
            key, hotp = kwargs['key'], kwargs['hotp']
            inst = UserCode.objects.get(code=str(key).lower())
            assert inst.hotp_at == hotp
            inst.increase_pages()
        except (KeyError, AssertionError, UserCode.DoesNotExist) as exc:
            logger.warning(f'QRResolveUserView.error {url} > {str(exc)}')
            return not_found_url
        data = dict(
            by='用户码',
            name=inst.user.name or '**',
            avatar=inst.user.cached_avatar,
            tail=inst.tail,
        )
        cache.set(cache_key, data, timeout=60 * 5)
        return redirect


class QRResolveSymbolView(RedirectView):
    """ 场景码页面解析 """

    permanent = False

    def get_redirect_url(self, **kwargs):
        url = self.request.build_absolute_uri()
        if not check_qrurl_sign(url):
            logger.warning(f'QRResolveSymbolView.check_qrurl_sign__fail {url}')
            return not_found_url
        cache_key, redirect = url_timed_hash_redirect(url)
        if cache.ttl(cache_key) > 100:
            return redirect
        try:
            key, hotp = kwargs['key'], kwargs['hotp']
            inst = Symbol.objects.get(symbol=str(key).lower())
            assert inst.hotp_at == hotp and inst.is_open
            inst.increase_pages()
        except (KeyError, AssertionError, Symbol.DoesNotExist) as exc:
            logger.warning(f'QRResolveSymbolView.error {url} > {str(exc)}')
            return not_found_url
        data = dict(
            by='场景码',
            tail=inst.tail,
            name=inst.user.name or '**',
            avatar=inst.user.cached_avatar,
            title=inst.title, scened=inst.scened,
        )
        cache.set(cache_key, data, timeout=60 * 5)
        return redirect


class QRImagePageView(TemplateView):
    """ 二维码页面浏览器预览 """

    template_name = 'qrimage/qrimg-view.html'

    def dispatch(self, *args, **kwargs):
        return cache_page(60)(super().dispatch)(*args, **kwargs)

    def get_context_data(self, **kwargs):
        kwargs = super().get_context_data(**kwargs)
        cache_key = f"qrimgurlhash:{kwargs['hashed']}"
        data = cache.get(cache_key)
        if not isinstance(data, dict):
            raise Http404
        cache.expire(cache_key, timeout=60 * 5)
        kwargs.update(**data)
        return kwargs
