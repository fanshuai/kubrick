"""
数据获取及缓存
"""
import logging
import functools
from sentry_sdk import capture_message, capture_exception

from server.constant import mochoice as mc

logger = logging.getLogger('kubrick.debug')


@functools.lru_cache
def dialog_user_name(usrid):
    """ 会话，对方用户名字 """
    from server.applibs.account.models import AuthUser
    name = AuthUser.objects.get(pk=usrid).name
    logger.info(f'dialog_user_name__done {usrid}: {name}')
    return name


@functools.lru_cache
def dialog_user_avatar(usrid):
    """ 会话，对方用户头像 """
    from server.applibs.account.models import UserProfile
    avatar = UserProfile.objects.get(pk=usrid).avatar_url
    return avatar


@functools.lru_cache
def mpa_user_openid(usrid):
    """ 小程序 openid """
    from server.applibs.account.models import OAuthWechatApp
    try:
        openid = OAuthWechatApp.objects.get(
            usrid=usrid, app_type=mc.WXAPPType.MPA,
        ).openid
    except Exception as exc:
        error_msg = f'mpa_user_openid__error {usrid} {str(exc)}'
        logger.exception(error_msg)
        capture_message(error_msg)
        capture_exception(exc)
        return ''
    return openid
