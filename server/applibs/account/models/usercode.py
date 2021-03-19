"""
用户码

实名认证后，其他用户可通过用户码联系你。
"""
import random
import logging
from io import BytesIO
from django.db import models
from django.core.exceptions import ValidationError
from django.utils.functional import cached_property
from sentry_sdk import configure_scope, capture_message, capture_exception
from django.core.files.base import ContentFile

from server.corelib.sequence import blaze, otpwd
from server.djextend.basemodel import BasicModel
from server.constant.validator import usercode_validator
from server.business.qrimg_util import get_user_qrcode_image
from server.third.aliyun.oss import oss_path
from server.business import qrcode_url

logger = logging.getLogger('kubrick.debug')


class UserCodeManager(models.Manager):
    """ UserCode.objects """

    def usercode_generate(self, usrid):
        """ 用户码生成 """
        inst, is_created = self.get_or_create(usrid=usrid)
        logger.info(f'usercode_generate__done {usrid} {is_created}')
        inst.generate_usercode()
        inst.qrimg_save()
        return inst

    def has_existed(self, code):
        """ 是否已存在 """
        is_exists = self.filter(code=code).exists()
        return is_exists


class UserCode(BasicModel):
    """ 用户码 """

    class Meta:
        verbose_name = 'UserCode'
        verbose_name_plural = verbose_name
        db_table = 'k_ac_user_code'
        ordering = ('-pk',)

    usrid = models.BigIntegerField('用户', primary_key=True)
    code = models.CharField(
        '用户码', max_length=7, unique=True, null=True, default=None,
        help_text='只能为7位纯字母', validators=[usercode_validator],
    )
    version = models.PositiveSmallIntegerField('版本', default=1)  # 32767
    qrimg = models.ImageField('二维码', upload_to=oss_path.usercode_qrimg, null=True, default=None)
    views = models.PositiveIntegerField('查询量', default=0)  # 扫码
    pages = models.PositiveIntegerField('页面量', default=0)

    objects = UserCodeManager()

    @property
    def fmt(self):
        """ 格式化，大写中间有空格 """
        code = f'{self.code[:3]} {self.code[-4:]}'.upper()
        return code

    @property
    def tail(self):
        """ 脱敏显示 """
        code = f'**{self.code[-4:]}'.upper()
        return code

    @cached_property
    def user(self):
        from server.applibs.account.models import AuthUser
        inst = AuthUser.objects.get(pk=self.usrid)
        return inst

    @property
    def hotp_at(self):
        hotp = otpwd.pyotp_hotp(f'{self.pk}:{self.code}')
        code = hotp.at(self.version)
        return code

    @property
    def qr_uri(self):
        """ 用户码内容 """
        uri = qrcode_url.get_qrcode_uri('page_qrimg_user', self.hotp_at, self.code)
        qruri = qrcode_url.qrurl_with_sign(uri)
        return qruri

    @property
    def qrimg_url(self):
        if not self.qrimg:
            return ''
        return self.qrimg.url

    def qrcode_reset(self):
        """ 用户重置二维码，HOTP码更新 """
        max_limit = 32000
        if self.version > max_limit:
            self.version = random.randint(1, max_limit)
        else:  # CombinedExpression is not JSON serializable
            self.version = models.F('version') + 1
        self.save(update_fields=['version', 'updated_at'])
        self.refresh_from_db()  # version 字段需刷新
        self.extra_log('reset', version=self.version)
        self.qrimg_save()
        return True, self.hotp_at

    def set_usercode(self, code) -> tuple:
        """ 设置用户码 """
        code = str(code).lower()
        if code == self.code:
            return True, code
        try:
            usercode_validator(code)
        except ValidationError as exc:
            return False, exc.message
        has_existed = self.__class__.objects.has_existed(code)
        if has_existed:
            return False, '用户码已存在'
        try:
            self.code = code
            self.save(update_fields=['code', 'updated_at'])
        except Exception as exc:
            capture_exception(exc)
            exc_type = type(exc).__name__
            with configure_scope() as scope:
                scope.set_extra('usrid', self.pk)
                scope.set_extra('exc_type', exc_type)
                scope.set_extra('code', code)
            capture_message('set_usercode_dberror', level='warning')
            logger.warning(f'set_usercode_dberror {self.pk} {code} {exc_type}')
            return False, '用户码暂不可用'
        else:
            self.extra_log('code', code=code)
        return True, code

    def generate_usercode(self):
        """ 生成随机用户码，重试99次 """
        if self.code:
            return None, 'has_done'
        tried = 1
        while tried <= 99:
            code = blaze.user_code_seq(self.pk)
            is_ok, reason = self.set_usercode(code)
            if is_ok:
                return True, code
            logger.warning(f'generate_usercode__tried {self.pk} {tried} {code}: {reason}')
            tried += 1
        with configure_scope() as scope:
            scope.set_extra('usrid', self.pk)
            scope.set_extra('tried', tried)
        capture_message('generate_usercode__fail', level='warning')
        logger.warning(f'generate_usercode__fail {self.pk} {tried}')
        raise RuntimeError(f'generate_usercode__fail {self.pk} {tried}')

    def qrimg_save(self):
        img = get_user_qrcode_image(self.user, self.qr_uri)
        with BytesIO() as buffer:
            img.save(buffer, format='png', optimize=True, quality=99)
            img_file = ContentFile(buffer.getvalue())
        self.qrimg.save(f'usercode-qrimg-{self.pk}.png', img_file, save=True)
        self.extra_log('qrimg', qrimg=self.qrimg_url)

    def increase_views(self):
        self.views = models.F('views') + 1
        self.save(update_fields=['views', 'updated_at'])

    def increase_pages(self):
        self.pages = models.F('pages') + 1
        self.save(update_fields=['pages', 'updated_at'])
