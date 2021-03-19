"""
扫描后的信息查询
"""
import logging
import functools
from dataclasses import dataclass
from urllib.parse import urlparse
from django.urls import resolve, Resolver404, ResolverMatch

from server.constant import mochoice as mc
from server.constant.normal import APP_NAME
from server.business import qrcode_url

logger = logging.getLogger('kubrick.debug')


@dataclass
class QRParse:
    """ 二维码解析结果 """
    url: str = ''
    key: str = ''
    hotp: str = ''
    reason: str = ''
    trigger: int = -1

    @property
    def is_ok(self):
        """ 是否有效 """
        is_yes = self.trigger in [
            mc.TriggerType.Symbol.value,
            mc.TriggerType.UserCode.value
        ]
        return is_yes


@functools.lru_cache
def qrcode_resolve_parse(url) -> QRParse:
    """ 二维码内容解析 """
    logger.info(f'qrcode_resolve_parse__url {url}')
    result = QRParse(url=url)
    parsed_url = urlparse(url)
    if not (parsed_url.scheme and parsed_url.netloc and parsed_url.path):
        result.reason = f'非{APP_NAME}二维码'
        return result
    try:
        match = resolve(parsed_url.path)
        assert isinstance(match, ResolverMatch)
        hotp = match.kwargs['hotp']
        key = match.kwargs['key']
    except (KeyError, ValueError, AssertionError, Resolver404) as exc:
        exc_type = type(exc).__name__
        logger.info(f'qrcode_resolve_parse__error {exc_type}')
        result.reason = f'非{APP_NAME}二维码'
        return result
    if not qrcode_url.check_qrurl_sign(url):
        result.reason = f'二维码已失效'
        return result
    url_name = match.url_name
    result.key, result.hotp = key, hotp
    if url_name in ['page_qr_symbol', 'page_qrimg_symbol']:
        result.trigger = mc.TriggerType.Symbol.value
    elif url_name in ['page_qr_user', 'page_qrimg_user']:
        result.trigger = mc.TriggerType.UserCode.value
    else:
        logger.warning(f'qrcode_resolve_parse__url_name_warn {url} {match.url_name}')
        result.reason = f'二维码无效'
    return result


@dataclass
class QRQuery:
    """ 二维码查询结果 """
    by: str = ''
    code: str = ''
    name: str = ''
    title: str = ''
    avatar: str = ''
    self: bool = False
    isPre: bool = False
    logged: bool = False
    convid: str = ''
    selfdom: str = ''
    reason: str = ''
    spuid: str = ''

    @property
    def is_ok(self):
        """ 是否成功 """
        return not self.reason


def qrcode_review_query(qr_parse: QRParse, usrid) -> QRQuery:
    """ 扫码预览信息查询 """
    from server.applibs.convert.models import Contact
    from server.applibs.account.models import UserCode, AuthUser
    from server.applibs.release.models import Symbol, Publication
    touch_user = None
    key = str(qr_parse.key).lower()
    qr_query = QRQuery(by='二维码', code=str(key).upper())
    assert qr_parse.is_ok, f'qr_parse__not_ok {qr_parse}'
    if qr_parse.trigger == mc.TriggerType.Symbol:
        qr_query.by = '场景码'
        try:
            symbol = Symbol.objects.get(symbol=key)
            assert symbol.is_open and symbol.hotp_at == qr_parse.hotp
            touch_user = symbol.user
            assert touch_user.is_active
        except Symbol.DoesNotExist:
            usable_pub = Publication.objects.get_usable_publication(key)
            if isinstance(usable_pub, Publication):
                qr_query.spuid = usable_pub.spuid
                qr_query.by = usable_pub.scened
                qr_query.code = usable_pub.fmt
                qr_query.isPre = True
            else:
                qr_query.reason = '二维码无效或暂不可用'
        except (KeyError, AssertionError):
            logger.warning(f'qrcode_review_query__no_symbol {key}')
            qr_query.reason = '二维码暂不可用或无效'
        else:
            if touch_user.pk != usrid:
                symbol.increase_views()
            qr_query.spuid = symbol.spuid
            qr_query.name = touch_user.name
            qr_query.selfdom = symbol.get_selfdom
            qr_query.title = symbol.title
            qr_query.by = symbol.scened
            qr_query.code = symbol.tail
    else:
        qr_query.by = '用户码'
        assert qr_parse.trigger == mc.TriggerType.UserCode
        try:
            uc_info = UserCode.objects.get(code=key)
            assert uc_info.hotp_at == qr_parse.hotp
            touch_user = uc_info.user
            assert touch_user.is_active
        except (KeyError, AssertionError, UserCode.DoesNotExist, AuthUser.DoesNotExist):
            logger.warning(f'qrcode_review_query__no_usercode {key}')
            qr_query.reason = '二维码无效或暂不可用'
        else:
            if touch_user.pk != usrid:
                uc_info.increase_views()
            qr_query.selfdom = touch_user.profile.bio
            qr_query.code = uc_info.tail
    if qr_query.is_ok and isinstance(touch_user, AuthUser):
        qr_query.name = touch_user.name
        qr_query.self = touch_user.pk == usrid
        qr_query.avatar = touch_user.profile.avatar_url
        qr_query.convid = Contact.objects.get_exist_convid(usrid, touch_user.pk)
    qr_query.logged = isinstance(usrid, int) and usrid > 0
    logger.info(f'qrcode_review_query__done {key}')
    return qr_query


def get_scan_qrcode_query(qr_urls):
    """ 根据二维码识别结果，获取用户码或场景码 """
    for url in qr_urls:
        result = qrcode_resolve_parse(url)
        if not result:
            continue
        return result
    return None


def get_ocr_vehicle_query(veh_type, veh_num):
    """ 根据车牌号OCR别识别结果，获取用户码或场景码 """
    trigger = mc.TriggerType.OCR
    vtype = mc.TYPE_VEHICLE_DIC[veh_type]
    result = dict(trigger=trigger, type=vtype, typed=veh_type, num=veh_num)
    return result
