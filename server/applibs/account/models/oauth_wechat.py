"""
微信登录认证
"""
import logging
from django.db import models
from sentry_sdk import capture_message, capture_exception

from server.constant import mochoice as mc
from server.corelib.dealer.deal_time import get_now
from server.djextend.basemodel import BasicModel, BIDModel
from server.third.wechat.wx_apis import WXCodeSession
from server.third.wechat.crypte import wx_data_decrypt
from server.corelib.hash_id import pk_hashid_decode

logger = logging.getLogger('kubrick.debug')


class OAuthWechatManager(models.Manager):

    def oauth_wechat_mpa_goc(self, code, encrypted, iv):
        """ 微信小程序OAuth记录 """
        try:
            if len(code) > 20:  # 微信Code，兼容老逻辑
                inst_app = OAuthWechatApp.objects.oauth_wechat_mpapp_up(code)
            else:
                app_id = pk_hashid_decode(code)
                inst_app = OAuthWechatApp.objects.get(pk=app_id)
            context = wx_data_decrypt(encrypted, inst_app.session_key, iv)
            unionid = context['unionId']
        except (IndexError, OAuthWechatApp.DoesNotExist) as exc:
            exc_msg = f'wx_get_session_key__error {str(exc)}'
            logger.exception(exc_msg)
            capture_message(exc_msg)
            capture_exception(exc)
            raise Exception('获取登录凭证失败')
        except Exception as exc:
            exc_msg = f'wx_data_decrypt__error {str(exc)}'
            logger.exception(exc_msg)
            capture_message(exc_msg)
            capture_exception(exc)
            raise Exception('登录凭证已失效请重试')
        from server.applibs.account.models.authuser import AuthUser
        inst_wx, is_created = self.get_or_create(unionid=unionid, defaults=dict(context=context))
        if is_created:
            inst_wx.load_wechat_info()
            inst_wx.link_at = get_now()
            inst_wx.usrid = AuthUser.objects.create_authuser(inst_wx.name).pk
            inst_wx.save(update_fields=['usrid', 'link_at', 'updated_at'])
            inst_wx.wxinfo_sync_profile()
        else:
            inst_wx.context = context
            inst_wx.save(update_fields=['context', 'updated_at'])
            inst_wx.load_wechat_info()
        inst_wx.openids[mc.WXAPPType.MPA.value] = inst_app.openid
        inst_wx.save(update_fields=['openids', 'updated_at'])
        inst_app.unionid, inst_app.usrid = unionid, inst_wx.usrid
        inst_app.save(update_fields=['unionid', 'usrid', 'updated_at'])
        logger.info(f'oauth_wechat_mpa_goc__done {inst_wx.pk} {is_created}')
        return inst_wx


class OAuthWechat(BasicModel, BIDModel):
    """
    微信登录认证
    """

    class Meta:
        verbose_name = 'OAuthWechat'
        verbose_name_plural = verbose_name
        index_together = ['gender', 'country', 'province', 'city']
        db_table = 'k_ac_oauth_wechat'
        ordering = ('-pk',)

    unionid = models.CharField('平台唯一标识', max_length=50, unique=True)
    openids = models.JSONField('不同应用标识', db_index=True, default=dict)
    usrid = models.BigIntegerField('用户', unique=True, null=True, default=None)
    nick_name = models.CharField('昵称', max_length=100, db_index=True, default='')
    gender = models.PositiveSmallIntegerField('性别', choices=mc.UserGender.choices, default=0)
    country = models.CharField('国家', max_length=200, default='')
    province = models.CharField('省份', max_length=200, default='')
    city = models.CharField('城市', max_length=200, default='')
    avatar = models.URLField('头像图片URL', default='')
    context = models.JSONField('用户信息', default=dict)
    link_at = models.DateTimeField('绑定时间', null=True, db_index=True)

    objects = OAuthWechatManager()

    @property
    def name(self):
        return self.nick_name

    @property
    def user(self):
        if not self.usrid:
            return None
        inst = self.get_user(self.usrid)
        return inst

    @property
    def user_dic(self):
        if not self.usrid:
            return None
        from server.applibs.account.schema.serializer import UserSelfSerializer
        dic = UserSelfSerializer(instance=self.user).data
        return dic

    @property
    def mpa_openid(self):
        """ 小程序Openid """
        openid = self.openids[mc.WXAPPType.MPA]
        return openid

    def load_wechat_info(self):
        """ 更新微信用户信息 """
        self.avatar = self.context.get('avatarUrl', '')
        self.nick_name = self.context.get('nickName', '')
        up_fields = ['gender', 'country', 'province', 'city']
        for field in up_fields:
            setattr(self, field, self.context[field])
        up_fields.extend(['avatar', 'nick_name', 'updated_at'])
        self.save(update_fields=up_fields)

    def bind_user(self, user):
        from .authuser import AuthUser
        assert isinstance(user, AuthUser)
        if self.usrid == user.pk:
            logger.info(f'oauth_wechat_bind_user__same {self.pk}:{self.usrid}')
            return  # 已绑定过相同用户
        if self.usrid:
            logger.warning(f'oauth_wechat_bind_user__warn {self.pk}:{self.usrid} {user.pk}')
            return
        self.usrid = user.pk
        self.link_at = get_now()
        self.save(update_fields=['usrid', 'link_at', 'updated_at'])

    def wxinfo_sync_profile(self):
        """ OAuth微信信息同步 """
        from .authuser import UserProfile
        profile = UserProfile.objects.get(usrid=self.usrid)
        profile.oauth_wechat_profile_sync(self)
        logger.info(f'wxinfo_sync_profile__done {self.usrid}')


class OAuthWechatAppManager(models.Manager):

    def oauth_wechat_mpapp_up(self, code):
        """ 微信小程序WXCodeSession """
        try:
            openid, skey = WXCodeSession(code=code).get_result()
        except Exception as exc:
            exc_msg = f'wx_code_session__error'
            logger.warning(f'{exc_msg} {str(exc)}')
            logger.exception(exc_msg)
            capture_message(exc_msg)
            capture_exception(exc)
            raise Exception('登录凭证校验失败')
        inst_app, is_created = self.get_or_create(
            app_type=mc.WXAPPType.MPA,
            openid=openid,
        )
        inst_app.session_key = skey
        inst_app.session_at = get_now()
        inst_app.save(update_fields=['session_key', 'session_at', 'updated_at'])
        logger.info(f'oauth_wechat_mpapp_up__done {openid} {inst_app.pk} {is_created}')
        return inst_app


class OAuthWechatApp(BasicModel, BIDModel):
    """
    微信登录认证应用标识
    """

    class Meta:
        verbose_name = 'OAuthWechatApp'
        verbose_name_plural = verbose_name
        unique_together = ('openid', 'app_type')
        db_table = 'k_ac_oauth_wechat_app'
        ordering = ('-pk',)

    openid = models.CharField('应用标识', max_length=50, db_index=True, default='')
    app_type = models.CharField('应用类型', max_length=20, choices=mc.WXAPPType.choices)
    unionid = models.CharField('平台唯一标识', max_length=50, db_index=True, default='')
    session_at = models.DateTimeField('会话更新时间', null=True, default=None)
    session_key = models.CharField('会话密钥', max_length=50, default='')
    usrid = models.BigIntegerField('用户', db_index=True, default=0)  # 冗余

    objects = OAuthWechatAppManager()

    @property
    def user_info(self):
        inst = self.get_user(self.usrid)
        return inst
