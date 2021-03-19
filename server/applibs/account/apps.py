import logging
from django.conf import settings
from django.apps import AppConfig
from rest_framework.request import Request
from django.db.models.signals import post_save
from django.contrib.auth import signals as auth_signals

from kubrick.initialize import IS_DJADMIN

logger = logging.getLogger('kubrick.debug')


class AccountConfig(AppConfig):
    name = 'server.applibs.account'
    verbose_name = '用户体系'

    def ready(self):
        post_save.connect(authuser_post_save_handler, sender=settings.AUTH_USER_MODEL)
        if IS_DJADMIN:
            logger.info(f'signals__user_logged_in__djadmin_ignore')
            logger.info(f'signals__user_logged_out__djadmin_ignore')
            logger.info(f'signals__user_login_failed__djadmin_ignore')
            return
        auth_signals.user_logged_in.connect(authuser_logged_in_handler)
        auth_signals.user_logged_out.connect(authuser_logged_out_handler)
        auth_signals.user_login_failed.connect(authuser_login_failed_handler)


def authuser_post_save_handler(**kwargs):
    """ 用户资料、用户码 记录创建 """
    from server.applibs.account.models import AuthUser, UserCode, UserProfile
    if not kwargs.get('sender') == AuthUser:
        return
    is_created, instance = kwargs.get('created'), kwargs.get('instance')
    if not (is_created and isinstance(instance, AuthUser)):
        return
    UserProfile.objects.get_or_create(usrid=instance.pk)
    UserCode.objects.usercode_generate(usrid=instance.pk)


def authuser_logged_in_handler(**kwargs):
    from server.applibs.account.models import UserDevice
    request = kwargs['request']
    if not isinstance(request, Request):
        logger.warning(f'authuser_logged_in_handler__not_drf_request')
        return
    UserDevice.objects.device_logged(request)
    session_key = request.session.session_key
    logger.info(f'authuser_logged_in_handler__done {session_key}')


def authuser_logged_out_handler(**kwargs):
    logger.info(f'authuser_logged_out_handler__info {kwargs}')


def authuser_login_failed_handler(**kwargs):
    logger.info(f'authuser_login_failed_handler__info {kwargs}')
