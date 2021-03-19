import json
import logging
import phonenumbers
from django.db import models, transaction
from django.utils.functional import cached_property
from phonenumbers import PhoneNumberFormat as PNFormat
from phonenumbers import carrier, geocoder
from mirage import fields as mg_fields

from server.constant import mochoice as mc
from server.corelib.sequence import idshift
from server.corelib.hash_id import pk_hashid_decode
from server.djextend.basemodel import BasicModel, BIDModel
from server.third.aliyun.dayu import sms_action, sms_constant
from server.corelib.dealer.deal_time import get_now
from server.corelib.dealer import format_phonenumber
from server.constant.normal import COUNTRY_CODES

logger = logging.getLogger('kubrick.debug')


class PhoneManager(models.Manager):

    def get_phone(self, number, **kwargs):
        """ 手机号获取 """
        number, msg = format_phonenumber(number)
        if not number:
            logger.warning(f'get_phone__parse_error {number} {msg}')
            raise ValueError(f'Phone number parse error: {msg}.')
        kwargs['shahash'] = idshift.hash_sha1(number)
        inst, is_created = self.get_or_create(number=number, defaults=kwargs)
        logger.info(f'get_phone__created {inst.pk} {is_created} {inst.usrid} {inst.show}')
        if is_created:
            inst.check_context()
        return inst

    def user_phone_qs(self, usrid):
        """ 用户手机号列表 """
        qs = self.filter(usrid=usrid, is_verified=True).order_by('order', 'pk')
        return qs

    def user_phone_main(self, usrid):
        """ 用户主手机号 """
        phone = self.user_phone_qs(usrid=usrid).first()
        return phone

    def check_phone_exist(self, number):
        """ 手机号是否已注册 """
        number, msg = format_phonenumber(number)
        if not number:
            logger.warning(f'check_phone_exist__parse_error {number} {msg}')
            return False
        is_exists = self.filter(number=number, usrid__gt=0).exists()
        return is_exists


class Phone(BasicModel, BIDModel):
    """ 手机号绑定，用户可绑定1~5个 """

    class Meta:
        verbose_name = 'Phone'
        verbose_name_plural = verbose_name
        index_together = ['carrier', 'nation', 'region', 'is_verified']
        db_table = 'k_ac_phone'
        ordering = ('-pk',)

    limit = 3  # 用户手机号绑定数量限制
    shahash = models.CharField('SHA1签名', max_length=50, unique=True)
    number = mg_fields.EncryptedCharField(verbose_name='手机号', max_length=50, unique=True)  # E164，加密
    national = mg_fields.EncryptedCharField(verbose_name='号码', max_length=50, db_index=True, default='')
    usrid = models.BigIntegerField('用户', db_index=True, default=0)
    carrier = models.CharField('运营商', max_length=50, default='')
    nation = models.CharField('国家', max_length=20, default='')
    region = models.CharField('归属地', max_length=50, default='')
    is_verified = models.BooleanField('已验证', default=False)
    verified_at = models.DateTimeField('验证时间', null=True, default=None)
    order = models.PositiveSmallIntegerField('顺序', default=0)

    objects = PhoneManager()

    @cached_property
    def parse_info(self):
        info = phonenumbers.parse(self.number, None)
        return info

    @property
    def user(self):
        if not self.usrid:
            return None
        info = self.get_user(self.usrid)
        return info

    @property
    def is_main(self):
        if not (self.usrid and self.is_verified):
            return False
        is_ok = self.order == 0
        return is_ok

    @property
    def sibling_qs(self):
        """ 该用户下其他手机号 """
        objects = self.__class__.objects
        if self.usrid and self.is_verified:
            qs = objects.filter(
                usrid=self.usrid, is_verified=True,
            ).exclude(pk=self.pk).order_by('order', 'pk')
        else:
            qs = objects.none()
        return qs

    @property
    def tail(self):
        """ 尾号 """
        return f'**{self.number[-4:]}'

    @property
    def show(self):
        """ 脱敏显示 """
        n = len(self.national)
        if self.country in COUNTRY_CODES and n == 11:
            s = f"{self.national[:1]}**{self.national[3:4]}***{self.national[-4:]}"
        elif n > 9:
            cut = n - 6
            s = f"{self.national[:2]}{'*' * cut}{self.national[-4:]}"
        else:
            cut = n - 3
            s = f"{self.national[:1]}{'*' * cut}{self.national[-2:]}"
        return s

    @property
    def summary(self):
        desc = f'{self.pk} {self.usrid} {self.show}'
        return desc

    @property
    def country(self):
        code = self.parse_info.country_code
        return code

    @property
    def fmt_natl(self):
        """ 国内号码格式化 """
        fmt = phonenumbers.format_number(self.parse_info, PNFormat.NATIONAL)
        return fmt

    @property
    def fmt_intl(self):
        """ 国际号码格式化 """
        fmt = phonenumbers.format_number(self.parse_info, PNFormat.INTERNATIONAL)
        return fmt

    def check_context(self):
        self.national = str(self.parse_info.national_number)
        self.carrier = carrier.name_for_number(self.parse_info, 'en')
        self.nation = geocoder.country_name_for_number(self.parse_info, 'en')
        self.region = geocoder.description_for_number(self.parse_info, 'en')
        up_fields = ['national', 'carrier', 'nation', 'region', 'updated_at']
        self.save(update_fields=up_fields)

    @transaction.atomic
    def set_main(self):
        """ 设为主手机号 """
        self.refresh_from_db()
        if not (self.usrid and self.is_verified):
            logger.info(f'set_main__not_verified {self.summary}')
            return False
        self.order = 0
        up_fields = ['order', 'updated_at']
        self.save(update_fields=up_fields)
        for index, phone in enumerate(self.sibling_qs):
            phone.order = index + 1
            phone.save(update_fields=up_fields)
        logger.info(f'set_main__done {self.pk} {self.show}')
        return True

    def user_phone_bind(self, usrid):
        """ 关联用户 """
        assert usrid > 0, f'user_phone_bind__no_user {self.pk}'
        if self.usrid == usrid:
            logger.warning(f'user_phone_bind__done {self.pk} {usrid}')
            return True, '已绑定'
        if self.usrid:
            self.extra_log('bind', usrid=self.usrid, new=usrid, type='repeat')
            logger.warning(f'user_phone_bind__repeat {self.pk} {self.usrid}')
            return False, '已被绑定'
        self.usrid = usrid
        self.is_verified = True
        self.verified_at = get_now()
        self.save(update_fields=['usrid', 'is_verified', 'verified_at', 'updated_at'])
        self.extra_log('usrid', usrid=usrid, type='create')
        return True, '成功'

    def captcha_send_for_sign(self):
        """ 验证码发送，仅登录 """
        assert self.usrid > 0, f'captcha_send_for_sign__no_user {self.pk}'
        ret = PNVerify.objects.pnvc_send(self.pk, mc.PNVScene.Sign)
        logger.info(f'captcha_send_for_sign__done {self.summary} {ret}')
        return ret

    def captcha_verify_for_sign(self, code):
        """ 验证码验证，仅登录 """
        assert self.usrid > 0, f'captcha_send_for_sign__no_user {self.pk}'
        is_ok = PNVerify.objects.pnvc_verify(self.pk, code, mc.PNVScene.Sign)
        if not is_ok:
            return None
        return self.user

    def captcha_send_for_bind(self):
        """ 验证码发送，用户绑定新手机号 """
        if self.usrid > 0:
            return False, '手机号已被绑定'
        ret = PNVerify.objects.pnvc_send(self.pk, mc.PNVScene.Bind)
        logger.info(f'captcha_send_for_bind__done {self.summary} {ret}')
        return True, ret

    def captcha_verify_for_bind(self, code, usrid):
        """ 验证码验证，用户绑定新手机号 """
        if self.usrid > 0:
            return False, '手机号已被绑定'
        assert isinstance(usrid, int) and usrid > 0, usrid
        is_ok = PNVerify.objects.pnvc_verify(self.pk, code, mc.PNVScene.Bind)
        if not is_ok:
            return False, '验证码不正确'
        if self.usrid > 0:
            return False, '手机号已被绑定'
        is_ok, reason = self.user_phone_bind(usrid)
        return is_ok, reason

    def captcha_send_for_unbind(self):
        """ 验证码发送，解除绑定手机号 """
        if not self.is_verified:
            return False, '手机号未绑定'
        if self.is_main:
            return False, '主手机号无法解除绑定'
        ret = PNVerify.objects.pnvc_send(self.pk, mc.PNVScene.Unbind)
        logger.info(f'captcha_send_for_unbind__done {self.summary} {ret}')
        return True, ret

    def captcha_verify_for_unbind(self, code):
        """ 验证码验证，解除绑定手机号 """
        is_ok = PNVerify.objects.pnvc_verify(self.pk, code, mc.PNVScene.Unbind)
        if not is_ok:
            return False, '验证码不正确'
        if not self.is_verified:
            return False, '手机号未绑定'
        if self.is_main:
            return False, '主手机号无法解除绑定'
        self.usrid = 0
        self.order = 0
        self.verified_at = None
        self.is_verified = False
        up_fields = ['usrid', 'order', 'is_verified', 'verified_at', 'updated_at']
        self.save(update_fields=up_fields)
        self.extra_log('usrid', usrid=0, type='unbind')
        return True, self.user

    def captcha_send_for_symbol_strike(self):
        """ 验证码发送，场景码删除 """
        if not (self.usrid and self.is_verified):
            return False, '手机号信息不正确'
        ret = PNVerify.objects.pnvc_send(self.pk, scene=mc.PNVScene.UNSymbol)
        logger.info(f'captcha_send_for_sign__done {self.summary} {ret}')
        return True, ret

    def captcha_verify_for_symbol_strike(self, code):
        """ 验证码验证，场景码删除 """
        if not (self.usrid and self.is_verified):
            return False
        is_ok = PNVerify.objects.pnvc_verify(self.pk, code, mc.PNVScene.UNSymbol)
        return is_ok


class PNVerifyManager(models.Manager):
    """ PNVerify.objects """

    def pnvc_send(self, phoneid, scene):
        """ 短信验证码发送，50秒内有记录不重发 """
        now = get_now()
        seconds_ago = now.add(seconds=-50)
        pnv_qs = self.filter(
            phoneid=phoneid, scene=scene,
            created_at__gt=seconds_ago,
            is_verified=False,
        )
        if pnv_qs.exists():
            send_dic = dict(
                phoneid=phoneid, scene=scene,
                seconds_ago=seconds_ago.isoformat(),
                now=now.isoformat(),
                pnv_count=pnv_qs.count(),
            )
            send_info = json.dumps(send_dic, sort_keys=True)
            logger.info(f'pnvc_just_sent {send_info}')
            return False, None
        template = sms_constant.SMS_CODE_SCENE_MAP[scene]
        inst = self.create(phoneid=phoneid, scene=scene, template=template)
        inst.sms_code_send()
        return True, inst.pk

    def pnvc_verify(self, phoneid, code, scene):
        """ 短信验证码验证，过去6分钟内未使用的验证码 """
        now = get_now()
        minutes_ago = now.add(minutes=-6)
        pnv_qs = self.filter(
            phoneid=phoneid, scene=scene,
            created_at__gt=minutes_ago,
            is_verified=False,
        ).order_by('-pk')
        for pnv in pnv_qs:
            is_ok, msg = pnv.sms_code_verify(code)
            if is_ok:
                return True
        return False

    def sms_code_report_receipt(self, dic):
        """ 验证码短信发送回执MNS订阅 """
        try:
            assert isinstance(dic, dict)
            bid = pk_hashid_decode(dic['tid'])
            inst = self.get(pk=bid, bizid=dic['biz_id'])
            is_ok = inst.report_receipt(dic)
        except (IndexError, AssertionError, PNVerify.DoesNotExist) as exc:
            logger.warning(f'sms_code_report_receipt__error {dic} {str(exc)}')
            is_ok = True
        return is_ok


class PNVerify(BasicModel, BIDModel):
    """ 手机号短信验证 """

    class Meta:
        verbose_name = 'PNVerify'
        verbose_name_plural = verbose_name
        db_table = 'k_ac_pnverify'
        ordering = ('-pk',)

    phoneid = models.BigIntegerField('手机号ID', db_index=True)
    captcha_hmac = models.CharField('验证码签名', max_length=50, default='')
    captcha_at = models.DateTimeField('发送时间', null=True, default=None)
    verified_at = models.DateTimeField('验证时间', null=True, default=None)
    is_verified = models.BooleanField('是否已验证', default=False)
    scene = models.PositiveSmallIntegerField(choices=mc.PNVScene.choices, default=0)
    status = models.SmallIntegerField('发送状态', choices=mc.SMSStatus.choices, default=0)
    bizid = models.CharField('回执', db_index=True, max_length=50, default='')
    template = models.CharField('模板', max_length=50, default='')
    sign = models.CharField('短信签名', max_length=25, default='')

    objects = PNVerifyManager()

    @property
    def sms_outid(self):
        """ 短信发送外部ID """
        return f'code-{self.hid}'

    @cached_property
    def phone_info(self):
        info = Phone.objects.get(pk=self.phoneid)
        return info

    @property
    def number(self):
        number = self.phone_info.number
        return number

    @property
    def usrid(self):
        number = self.phone_info.usrid
        return number

    @property
    def is_status_final(self):
        """ 是否已终态 """
        is_yes = self.status in [
            mc.SMSStatus.Success,
            mc.SMSStatus.Failure,
        ]
        return is_yes

    def sms_code_send(self):
        """ 短信验证码发送 """
        if self.is_verified:
            return f'is_verified'
        self.captcha_at = get_now()
        code = idshift.generate_captcha()
        self.captcha_hmac = idshift.hmac_hash(self.pk, code)
        self.save(update_fields=['captcha_hmac', 'captcha_at'])
        try:
            result = sms_action.sms_send__code(self, code)
            self.extra['resp_send'] = result
            self.bizid = result.get('BizId', '')
            self.status = mc.SMSStatus.Waiting if self.bizid else mc.SMSStatus.Init
            self.save(update_fields=['status', 'bizid', 'extra', 'updated_at'])
        except Exception as exc:
            self.extra['send_error'] = str(exc)
            self.save(update_fields=['extra', 'updated_at'])
            logger.warning(f'sms_code_send__error {str(exc)}')
            logger.exception(exc)
        return code

    def sms_code_verify(self, code):
        """ 短信验证码验证 """
        if self.is_verified:
            return None, 'is_verified'
        if not self.captcha_hmac == idshift.hmac_hash(self.pk, code):
            return False, 'failure'
        self.is_verified = True
        self.verified_at = get_now()
        self.save(update_fields=['is_verified', 'verified_at', 'updated_at'])
        return True, 'success'

    def sms_code_query(self):
        """ 主动查询回执状态 """
        if self.is_status_final:
            logger.info(f'sms_code_query__final {self.pk}')
            return
        if not self.bizid:
            logger.warning(f'sms_code_query__no_bizid {self.pk}')
            return
        try:
            result = sms_action.sms_query__code(self)
            self.status = result['SendStatus']
            self.extra['resp_query'] = result
            self.save(update_fields=['status', 'extra', 'updated_at'])
        except Exception as exc:
            self.extra['query_error'] = str(exc)
            self.save(update_fields=['extra', 'updated_at'])
            logger.warning(f'sms_code_query__error {str(exc)}')
            logger.exception(exc)

    def report_receipt(self, result):
        """ 短信发送回执MNS订阅 """
        if self.status in [mc.SMSStatus.Init, mc.SMSStatus.Waiting]:  # 回调时序问题
            self.status = mc.SMSStatus.Success if result['success'] else mc.SMSStatus.Failure
        self.save(update_fields=['status', 'updated_at'])
        self.extra_log('report', result=result)
        return True
