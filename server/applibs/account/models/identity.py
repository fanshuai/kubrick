"""
身份证、驾驶证，实名认证
"""
import logging
from django.db import models
from mirage import fields as mg_fields

from server.corelib.sequence import idshift
from server.corelib.dealer.deal_idcard import is_valid_idcard
from server.corelib.dealer.deal_time import get_now, get_tzcn_date_parse
from server.djextend.basemodel import BasicModel, BIDModel
from server.third.idcard import alicloudapi_idcard_verify
from server.third.aliyun import oss

logger = logging.getLogger('kubrick.debug')


class IDCardManager(models.Manager):
    """ IDCard.objects 方法定制 """

    @staticmethod
    def check_idcard_third(name, number):
        """ 第三方实名认证服务 """
        try:
            is_ok, msg = alicloudapi_idcard_verify(name, number)
        except Exception as exc:
            logger.warning(f'check_idcard_third__error {str(exc)}')
            logger.exception(exc)
            is_ok, msg = False, '认证服务异常，请稍后重试'
        return is_ok, msg

    def idcard_approve(self, img_front, img_back, front_dic, back_dic, usrid):
        assert isinstance(usrid, int) and usrid > 0, usrid
        if not all([front_dic.get('type') == 'front', back_dic.get('type') == 'back']):
            return False, '无法识别'
        if any([front_dic.get('_rate', 0) < 95, back_dic.get('_rate', 0) < 95]):
            return False, '无法准确识别'
        name = front_dic.get('name')
        end_date = back_dic.get('endDate')
        number = str(front_dic.get('number')).upper()
        if not (name and number and end_date):
            return False, '无法识别有效信息'
        if not is_valid_idcard(number):
            return False, '身份证号不合法'
        today = get_now().date()
        end_date = get_tzcn_date_parse(end_date)
        if end_date and ((end_date - today).days < 50):
            return False, '身份证已过期' if ((end_date - today).days < 0) else '身份证到期时间不足50天'
        if self.filter(number=number, is_valid=True).exclude(usrid=usrid).exists():
            return False, '已被其他用户认证'
        is_ok, third_msg = self.check_idcard_third(name, number)
        if not is_ok:
            return False, third_msg
        oss_keys = dict(front=img_front, back=img_back)
        defaults = dict(
            usrid=usrid,
            oss_keys=oss_keys,
            name=front_dic['name'],
            sex=front_dic['sex'],
            nationality=front_dic['nationality'],
            birth=get_tzcn_date_parse(front_dic['birth']),
            address=front_dic['address'],
            authority=back_dic['authority'],
            start_date=get_tzcn_date_parse(back_dic['startDate']),
            end_date=get_tzcn_date_parse(back_dic['endDate']),
        )
        inst, is_created = self.get_or_create(
            number=number,
            shahash=idshift.hash_sha1(number),
            defaults=defaults,
        )
        if not is_created:
            for k, v in defaults.items():
                setattr(inst, k, v)
            inst.save(update_fields=defaults.keys())
        inst.extra_log('third-msg', msg=third_msg)
        inst.extra_log('usrid', usrid=usrid)
        is_ok, resp = inst.img_hold_on()
        return is_ok, resp


class IDCard(BasicModel, BIDModel):
    """ 身份证 """

    class Meta:
        verbose_name = 'IDCard'
        verbose_name_plural = verbose_name
        index_together = ['sex', 'birth', 'nationality', 'is_valid']
        db_table = 'k_ac_idcard'
        ordering = ('-pk',)

    oss_keys = models.JSONField('身份证照片', default=dict)  # front、back
    shahash = models.CharField('SHA1签名', max_length=50, unique=True)
    usrid = models.BigIntegerField('用户', unique=True, null=True, default=None)
    number = mg_fields.EncryptedCharField(verbose_name='身份证号', max_length=100, unique=True)
    name = mg_fields.EncryptedCharField(verbose_name='姓名', max_length=200, default='')
    sex = models.CharField('性别', max_length=20, default='')
    nationality = models.CharField('民族', max_length=50, default='')
    birth = models.DateField('出生年月', null=True, default=None)
    address = mg_fields.EncryptedCharField(verbose_name='住址', max_length=255, default='')
    authority = mg_fields.EncryptedCharField(verbose_name='签发机构', max_length=255, default='')
    start_date = models.DateField('有效期开始日期', null=True, default=None)
    end_date = models.DateField('有效期结束日期', null=True, default=None)  # 可能为None: 长期
    is_valid = models.BooleanField('是否有效', default=False)
    # 身份证照片是否是复印件、身份证照片是否是翻拍

    objects = IDCardManager()

    @property
    def img_front(self):
        """ 身份证正面图片，带水印，60秒内有效 """
        oss_front = self.oss_keys['front']
        url = oss.oss_sign_url(oss_front, expires=60, watermark=True)
        return url

    @property
    def img_back(self):
        """ 身份证背面图片，带水印，60秒内有效 """
        oss_back = self.oss_keys['back']
        url = oss.oss_sign_url(oss_back, expires=60, watermark=True)
        return url

    def img_hold_on(self):
        """ 认证通过后图片迁移目录 """
        oss_keys = self.oss_keys
        oss_front, oss_back = oss_keys['front'], oss_keys['back']
        is_ok_front, new_front_key = oss.oss_idcard_hold_on(oss_front)
        oss_keys['front'] = new_front_key if is_ok_front else oss_front
        is_ok_back, new_back_key = oss.oss_idcard_hold_on(oss_back)
        oss_keys['back'] = new_back_key if is_ok_back else oss_back
        if not (is_ok_front and is_ok_back):
            return False, '图片拉取失败'
        self.is_valid = True
        self.oss_keys = oss_keys
        self.save(update_fields=['is_valid', 'oss_keys', 'updated_at'])
        return True, self
