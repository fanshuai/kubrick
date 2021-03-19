"""
用户登录设备管理
"""
import logging
import pendulum
from django.db import models
from django.conf import settings
from django.contrib.sessions.models import Session
from django.contrib.sessions.backends.base import SessionBase
from user_agents import parse as ua_parse
from sentry_sdk import capture_message
from importlib import import_module
from ipware import get_client_ip

from server.constant.normal import TZCN
from server.corelib.sequence import idshift
from server.djextend.basemodel import BasicModel, BIDModel
from server.corelib.dealer.deal_time import get_now, time_floor_ts, diff_humans

logger = logging.getLogger('kubrick.debug')
# noinspection PyUnresolvedReferences
SessionStore = import_module(settings.SESSION_ENGINE).SessionStore
assert issubclass(SessionStore, SessionBase)


class UserDeviceManager(models.Manager):

    def deviceinfo_update(self, data):
        """ 设备UA、及最后活跃时间更新 """
        if not data['usrid']:
            return
        trace = data['trace']
        key, usrid = data['key'], data['usrid']
        req_time = pendulum.parse(trace['now'])
        try:
            inst = self.get(key=key, usrid=usrid)
        except UserDevice.DoesNotExist:
            logger.info(f'deviceinfo_update__no_inst {usrid} {key}')
            return
        inst.last_uri = data['uri']
        inst.activated_at = req_time
        inst.check_user_agent(data['ua'])
        inst.req_count = models.F('req_count') + 1
        up_fields = ['req_count', 'activated_at', 'last_uri']
        inst.save(update_fields=up_fields)
        logger.info(f'deviceinfo_update__done {usrid} {key}')

    def device_logged(self, request):
        usrid = request.user.pk
        key = request.session.session_key
        if not (key and isinstance(usrid, int) and (usrid > 0)):
            logger.warning(f'device_logged__no_user {usrid} {key}')
            capture_message('device_logged__no_user', level='warning')
            return None
        referer = request.META.get('HTTP_REFERER', '')
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        client_ip, is_routable = get_client_ip(request)
        defaults = dict(
            usrid=usrid,
            client_ip=client_ip,
            is_routable=is_routable,
            referer=referer,
        )
        inst, is_created = self.get_or_create(key=key, defaults=defaults)
        logger.info(f'device_logged__not_created {inst.pk} {inst.usrid} {is_created}')
        inst.check_user_agent(user_agent)
        self.same_device_logout(usrid, inst)
        return inst

    def same_device_logout(self, usrid, device):
        """ 用户下相同设备之前Session退出登录 """
        assert isinstance(device, UserDevice)
        device_qs = self.filter(
            usrid=usrid,
            is_valid=True,
            app_type=device.app_type,
            device_name=device.device_name,
        ).exclude(pk=device.pk)
        keys = [d.pk for d in device_qs]
        for device in device_qs:
            device.logout(usrid, 'new login')
        logger.info(f'same_device_logout__done {usrid} {device.pk} {keys}')
        return keys

    def get_user_device_qs(self, usrid):
        """ 用户登录设备 """
        old_qs = self.filter(usrid=usrid, is_valid=True)
        for inst in old_qs:
            inst.check_valid()
        new_qs = self.filter(usrid=usrid, is_valid=True)
        return new_qs

    def user_device_list(self, usrid, key=''):
        """ 用户设备列表 """
        from server.applibs.account.schema.serializer import UserDeviceSerializer
        device_qs = self.get_user_device_qs(usrid=usrid).order_by('-activated_at')
        data = [UserDeviceSerializer(instance=inst, context={'key': key}).data for inst in device_qs]
        current = [one for one in data if one['current']]  # 排序：当前设备第一
        data = current + [one for one in data if not one['current']]
        return data


class UserDevice(BasicModel, BIDModel):
    """
    用户会话设备
    User devices
    """

    class Meta:
        db_table = 'k_ac_user_device'
        verbose_name = 'UserDevice'
        verbose_name_plural = verbose_name
        index_together = ['app_type', 'device_name', 'is_valid', 'is_online']
        ordering = ('-created_at',)

    key = models.CharField(max_length=40, unique=True)
    usrid = models.BigIntegerField('用户', db_index=True)
    client_ip = models.GenericIPAddressField('用户IP', null=True, default=True)
    is_routable = models.BooleanField('IP可公开路由', null=True, default=None)
    referer = models.CharField('来源地址', max_length=255, default='')
    user_agent = models.TextField('用户代理', default='')  # 255 长度不够用
    ua_info = models.JSONField('用户代理信息', db_index=True, default=dict)
    device_key = models.CharField('设备号', max_length=32, db_index=True)  # ua md5
    device_name = models.CharField('设备名称', max_length=100, default='')
    app_type = models.CharField('应用类型', max_length=50, default='')
    last_uri = models.URLField('最后访问', default='')
    activated_at = models.DateTimeField('最后活跃', db_index=True, auto_now_add=True)
    logout_at = models.DateTimeField('退出登录时间', null=True, db_index=True)  # 登录时间即创建时间
    version = models.CharField('应用版本', max_length=128, default='')
    req_count = models.PositiveIntegerField('请求量', default=0)
    is_online = models.BooleanField('是否在线', default=False)
    is_valid = models.BooleanField('是否有效', default=True)
    # API count, json with status code, last uri

    objects = UserDeviceManager()

    @property
    def session(self):
        try:
            session = Session.objects.get(pk=self.key)
        except Session.DoesNotExist:
            logger.info(f'session_key_not_exist {self.usrid} {self.key}')
            session = None
        return session

    @property
    def expire_at(self):
        """ 过期时间 """
        if not self.session:
            return None
        at = time_floor_ts(self.session.expire_date)
        return at

    @property
    def diff_activated(self):
        """ 最后活跃 """
        diff = diff_humans(self.activated_at)
        return diff

    def get_app_type(self):
        """ 客户端应用类型 """
        if 'MicroMessenger' in self.user_agent:
            if 'wechatdevtools' in self.user_agent:
                return '微信小程序开发工具'
            return '微信小程序'
        return '其他'

    @property
    def signin_date(self):
        """ 登录日期 """
        date_str = pendulum.instance(self.created_at).in_tz(TZCN).to_date_string()
        return date_str

    def check_user_agent(self, value: str):
        """ 根据UA，获取设备信息 """
        if not value or self.user_agent == value:
            return
        self.user_agent = value
        self.device_key = idshift.hash_md5(f'{self.usrid}:{value}')
        ua_info = ua_parse(self.user_agent)
        self.ua_info = dict(
            device=dict(
                family=ua_info.device.family,
                brand=ua_info.device.brand,
                model=ua_info.device.model,
            ),
            os=dict(
                family=ua_info.os.family,
                version=ua_info.os.version_string,
            ),
            browser=dict(
                family=ua_info.browser.family,
                version=ua_info.browser.version_string,
            )
        )
        self.app_type = self.get_app_type()
        self.device_name = ' '.join([i.strip() for i in str(ua_info).split('/')][:2])
        up_fields = ['app_type', 'user_agent', 'device_key', 'device_name', 'ua_info', 'updated_at']
        self.save(update_fields=up_fields)

    def check_valid(self):
        """ 检查是否有效 """
        if not self.is_valid:
            return False
        if not self.session:
            self.logout(self.usrid, 'no session')
            return False
        now = get_now()
        if self.session.expire_date < now:
            self.logout(self.usrid, 'expired')
            return False
        return True

    def update_expire(self):
        """ 根据最后活跃时间，自动续期Session，每天任务执行 """
        is_valid = self.check_valid()
        if not is_valid:
            return
        active_date = pendulum.instance(self.activated_at).in_tz(TZCN).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        assert isinstance(active_date, pendulum.DateTime)
        new_date = active_date.add(days=100)
        store = SessionStore(self.key)
        store.set_expiry(new_date)
        store.save()
        logger.info(f'update_expire__done {self.key} {self.usrid} > {new_date}')

    def logout(self, usrid, reason=''):
        """ 退出登录 """
        if not self.is_valid:
            return
        if not self.usrid == usrid:
            return
        store = SessionStore()
        assert isinstance(store, SessionBase)
        store.delete(self.key)
        self.is_valid = False
        self.logout_at = get_now()
        self.save(update_fields=['is_valid', 'logout_at', 'updated_at'])
        self.extra_log('logout', usrid=usrid, reason=reason)
