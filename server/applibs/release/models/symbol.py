import logging
from django.db import models
from django.utils.functional import cached_property

from server.constant import mochoice as mc
from server.corelib.sequence import otpwd
from server.corelib.dealer.deal_time import time_floor_ts
from server.djextend.basemodel import BasicModel, BIDModel
from server.constant.validator import symbol_validator
from server.business import qrcode_url

logger = logging.getLogger('kubrick.debug')


class SymbolManager(models.Manager):

    def user_symbol_qs(self, usrid):
        """ 用户的场景码 """
        qs = self.filter(usrid=usrid, status__in=[
            mc.SymbolStatus.Bound,
            mc.SymbolStatus.Closed,
        ]).order_by('-pk')
        return qs

    @staticmethod
    def count_trigger_update(symbol):
        """ 触发量 统计更新 """
        assert isinstance(symbol, Symbol)
        from server.applibs.convert.models import Message
        count = Message.objects.filter(
            msg_type=mc.MSGType.Trigger,
            symbol=symbol.symbol,
            is_del=False,
        ).count()
        symbol.ct_trigger = count
        symbol.save(update_fields=['ct_trigger', 'updated_at'])


class Symbol(BasicModel, BIDModel):
    """ 场景码 """

    class Meta:
        verbose_name = 'Symbol'
        verbose_name_plural = verbose_name
        index_together = ['scene', 'status', 'version']
        db_table = 'k_ls_symbol'
        ordering = ('-pk',)

    symbol = models.CharField(
        '场景码', max_length=10, unique=True, null=True, default=None,
        help_text='只能为10位纯字母', validators=[symbol_validator],
    )
    usrid = models.BigIntegerField('用户', db_index=True, default=0)
    scene = models.PositiveSmallIntegerField('场景', choices=mc.SymbolScene.choices, default=0)
    status = models.PositiveSmallIntegerField('状态', choices=mc.SymbolStatus.choices, default=0)
    title = models.CharField('别名', max_length=200, default='')
    ct_trigger = models.PositiveIntegerField('触发量', default=0)  # 触发创建会话
    bound_at = models.DateTimeField('绑定时间', db_index=True, null=True, default=None)
    selfdom = models.CharField('自定义签名', max_length=200, default='')  # 扫码展示内容
    version = models.PositiveSmallIntegerField('版本', default=1)  # 32767
    views = models.PositiveIntegerField('查询量', default=0)  # 扫码
    pages = models.PositiveIntegerField('页面量', default=0)

    objects = SymbolManager()

    @property
    def fmt(self):
        """ 格式化，大写中间有空格 """
        code = f'{self.symbol[:3]} {self.symbol[3:-4]} {self.symbol[-4:]}'.upper()
        return code

    @property
    def tail(self):
        """ 脱敏显示 """
        code = f'**{self.symbol[-4:]}'.upper()
        return code

    @property
    def qr_uri(self):
        """ 场景码内容 """
        uri = qrcode_url.get_qrcode_uri('page_qrimg_symbol', self.hotp_at, self.symbol)
        qruri = qrcode_url.qrurl_with_sign(uri)
        return qruri

    @cached_property
    def publication(self):
        from server.applibs.release.models import Publication
        inst = Publication.objects.get(symbol=self.symbol)
        return inst

    @property
    def spuid(self):
        sid = self.publication.spuid
        return sid

    @property
    def qrimg_url(self):
        url = self.publication.qrimg_url
        return url

    @property
    def scened(self):
        return self.get_scene_display()

    @property
    def get_selfdom(self):
        """ 场景码默认签名 """
        if self.selfdom:
            return self.selfdom
        if self.scene == mc.SymbolScene.Vehicle:
            value = '临时停靠 请多关照'
        else:
            value = ''
        return value

    @property
    def bound_date(self):
        if not self.bound_at:
            return None
        dt = time_floor_ts(self.bound_at).date()
        return dt

    @property
    def views_count(self):
        count = self.views + self.pages
        return count

    @property
    def user(self):
        inst = self.get_user(self.usrid)
        return inst

    @property
    def hotp_at(self):
        hotp = otpwd.pyotp_hotp(self.symbol)
        code = hotp.at(self.version)
        return code

    @property
    def is_usable(self):
        """ 是否可用 """
        is_yes = self.status in [
            mc.SymbolStatus.Bound,
            mc.SymbolStatus.Closed,
        ]
        is_active = self.user.is_active
        is_ok = is_yes and is_active
        return is_ok

    @property
    def is_closed(self):
        """ 是否关闭 """
        is_yes = self.status == mc.SymbolStatus.Closed
        return is_yes

    @property
    def is_open(self):
        """ 是否打开 """
        is_ok = self.status == mc.SymbolStatus.Bound
        return is_ok

    @property
    def is_user_active(self):
        """ 用户是否有效 """
        is_active = self.user.is_active
        return is_active

    def user_status(self, is_open=True):
        """ 用户设置状态 """
        if not self.is_usable:
            return self.status
        if is_open:
            self.status = mc.SymbolStatus.Bound
        else:
            self.status = mc.SymbolStatus.Closed
        self.save(update_fields=['status', 'updated_at'])
        self.extra_log('user-status', status=self.status)

    def set_title(self, title):
        """ 设置 别名 """
        self.title = title
        self.save(update_fields=['title', 'updated_at'])
        self.extra_log('title', title=title)

    def set_selfdom(self, selfdom):
        """ 设置 自定义签名 """
        self.selfdom = selfdom
        self.save(update_fields=['selfdom', 'updated_at'])
        self.extra_log('selfdom', selfdom=selfdom)

    def increase_views(self):
        self.views = models.F('views') + 1
        self.save(update_fields=['views', 'updated_at'])

    def increase_pages(self):
        self.pages = models.F('pages') + 1
        self.save(update_fields=['pages', 'updated_at'])

    def status_delete(self):
        if self.status in [
            mc.SymbolStatus.Deleted,
            mc.SymbolStatus.Invalid,
        ]:
            return
        self.status = mc.SymbolStatus.Deleted
        up_fields = ['status', 'updated_at']
        self.save(update_fields=up_fields)
