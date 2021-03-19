import logging
import pendulum
from django.db import models
from django.contrib.postgres import fields
from django.utils.functional import cached_property
from mirage import fields as mg_fields

from server.constant import mochoice as mc
from server.corelib.sequence import idshift
from server.third.aliyun.oss import oss_sign_url
from server.djextend.basemodel import BasicModel, BIDModel
from server.constant.normal import vehicle_small_types

logger = logging.getLogger('kubrick.debug')


class VehicleManager(models.Manager):

    def bind_vehicle_symbol(self, vlicense):
        """ 用户绑定车辆 """
        assert isinstance(vlicense, VehicleLicense)
        assert vlicense.is_verified, f'{vlicense.pk} {vlicense.reason}'
        vehicle_type, vehicle_num = vlicense.get_vehicle_type(), vlicense.plate_num
        shahash = idshift.hash_sha1(f'{vehicle_type}:{vehicle_num}')
        inst, is_created = self.get_or_create(
            shahash=shahash,
            vehicle_num=vlicense.plate_num,
            vehicle_type=vlicense.get_vehicle_type(),
        )
        if (not is_created) and inst.symbol:
            logger.warning(f'bind_vehicle_symbol__has_bind {inst.pk} {inst.symbol} {inst.usrid} > {vlicense.usrid}')
            if inst.usrid == vlicense.usrid:
                return False, '你已经绑定过该车辆'
            else:
                return False, '已被其他用户绑定'
        inst.usrid = vlicense.usrid
        inst.license_id = vlicense.pk
        inst.model_id = vlicense.model_info.pk
        inst.save(update_fields=['usrid', 'symbol', 'license_id', 'model_id', 'updated_at'])
        inst.extra_log('bind', usrid=inst.usrid, symbol=inst.symbol, license_id=inst.license_id)
        vlicense.model_info.checkout()
        return False, '该功能已下线'


class Vehicle(BasicModel, BIDModel):
    """ 车辆绑定信息，已行驶证OCR认证 """

    class Meta:
        verbose_name = 'Vehicle'
        verbose_name_plural = verbose_name
        unique_together = ('vehicle_num', 'vehicle_type')
        index_together = ['vehicle_type', 'relation']
        db_table = 'k_ls_vehicle'
        ordering = ('-pk',)

    usrid = models.BigIntegerField('用户', db_index=True, default=0)
    shahash = models.CharField('SHA1签名', max_length=50, unique=True)
    vehicle_num = models.CharField('车牌号', db_index=True, max_length=20)
    vehicle_type = models.PositiveSmallIntegerField('车牌类型', choices=mc.VehicleType.choices)
    symbol = models.CharField('场景码', max_length=10, unique=True, null=True, default=None)
    relation = models.PositiveSmallIntegerField('所有者关系', choices=mc.VehicleRelation.choices, default=0)
    model_id = models.PositiveIntegerField('车辆型号', db_index=True, default=0)
    license_id = models.BigIntegerField('行驶证ID', db_index=True, default=0)

    objects = VehicleManager()

    @cached_property
    def license_info(self):
        inst = VehicleLicense.objects.get(pk=self.license_id)
        return inst

    @property
    def model_info(self):
        if not self.model_id:
            return None
        inst = VehicleModel.objects.get(pk=self.model_id)
        return inst

    @property
    def summary(self):
        if not self.model_id:
            return self.get_vehicle_type_display()
        return self.model_info.summary

    def unbind(self):
        """ 解除场景码绑定 """
        usrid, symbol = self.usrid, self.symbol
        self.usrid, self.symbol = 0, None
        self.save(update_fields=['usrid', 'symbol', 'updated_at'])
        self.extra_log('unbind', usrid=usrid, symbol=symbol)


class VehicleLicenseManager(models.Manager):
    """ VehicleLicense.objects 方法定制 """

    def vehicle_license_add(self, oss_key, usrid):
        assert isinstance(usrid, int) and usrid > 0, usrid
        inst = self.create(oss_key=oss_key, usrid=usrid)
        inst.get_ocr_result()
        inst.check_verifid()
        return inst


class VehicleLicense(BasicModel, BIDModel):
    """ 车辆行驶证信息 """

    class Meta:
        verbose_name = 'VehicleLicense'
        verbose_name_plural = verbose_name
        index_together = ['vehicle_type', 'use_character', 'model', 'is_verified']
        db_table = 'k_ls_vehicle_license'
        ordering = ('-pk',)

    oss_key = models.URLField('图片路径', db_index=True, default='')
    usrid = models.BigIntegerField('用户', db_index=True, default=0)
    plate_num = models.CharField('车牌号', db_index=True, max_length=20, default='')
    vehicle_type = models.CharField('车辆类型', max_length=100, default='')
    use_character = models.CharField('车辆使用性质', max_length=100, default='')
    owner = mg_fields.EncryptedCharField(verbose_name='所有者名字', max_length=200, default='')
    address = mg_fields.EncryptedCharField(verbose_name='住址', max_length=255, default='')
    vin = mg_fields.EncryptedCharField(verbose_name='车辆识别代号', max_length=100, default='')
    engine_num = mg_fields.EncryptedCharField(verbose_name='发动机号码', max_length=100, default='')
    model = models.CharField('车辆品牌', max_length=200, default='')
    register_date = models.DateField('注册日期', null=True, default=None)
    issue_date = models.DateField('发证日期', null=True, default=None)
    reason = models.CharField('原因', max_length=200, default='')
    verified_at = models.DateTimeField('验证时间', null=True, default=None)
    is_verified = models.BooleanField('已验证', default=False)

    objects = VehicleLicenseManager()

    @cached_property
    def model_info(self):
        inst = VehicleModel.objects.get_vehicle_model(
            self.model, vehicle_type=self.vehicle_type
        )
        return inst

    @property
    def oss_url(self):
        """ OSS URL，无水印，60秒内有效 """
        url = oss_sign_url(self.oss_key)
        return url

    @property
    def url_watermark(self):
        """ OSS URL，带水印，99秒内有效 """
        url = oss_sign_url(self.oss_key, expires=99, watermark=True)
        return url

    @property
    def is_success(self):
        is_ok = self.vehicle_type and self.plate_num and self.owner
        return is_ok

    @property
    def is_support(self):
        """ 是否支持，仅支持 非营运的小型汽车或新能源车 """
        is_type_ok = self.get_vehicle_type() in mc.VehicleTypeSupport
        is_character_ok = self.use_character == '非营运'
        is_ok = is_type_ok and is_character_ok
        return is_ok

    def get_vehicle_type(self):
        """ 车辆类型转车牌类型 """
        if self.vehicle_type in vehicle_small_types:
            if len(self.plate_num) == 7:
                return mc.VehicleType.Small  # 小型汽车
            elif len(self.plate_num) == 8:
                return mc.VehicleType.Energy  # 新能源车
        return None

    def get_ocr_result(self):
        """ OCR查询 """
        if self.is_success:
            logger.info(f'vehicle_license_get_ocr_result__is_success {self.pk}')
            return
        from server.applibs.outside.models import ImageOcr
        inst = ImageOcr.objects.image_ocr_create(
            self.oss_key, mc.OCRType.VehicleLicenseFront, usrid=self.usrid
        )
        if not inst.is_victor:
            logger.warning(f'vehicle_license_get_ocr_result__not_victor {self.pk}')
            return
        data = inst.result_dic
        try:
            self.vin = data['vin']
            self.model = data['model']
            self.owner = data['owner']
            self.address = data['address']
            self.plate_num = data['plateNum']
            self.engine_num = data['engineNum']
            self.vehicle_type = data['vehicleType']
            self.use_character = data['useCharacter']
            self.issue_date = pendulum.parse(data['issueDate'], exact=True)
            self.register_date = pendulum.parse(data['registerDate'], exact=True)
            up_fields = [
                'vin', 'model', 'owner', 'address', 'plate_num', 'engine_num',
                'vehicle_type', 'use_character', 'issue_date', 'register_date', 'updated_at',
            ]
            self.save(update_fields=up_fields)
        except Exception as exc:
            self.reason = '行驶证信息识别不完整'
            self.save(update_fields=['reason', 'updated_at'])
            logger.exception(f'vehicle_license_ocr_result__save_error {str(exc)}')

    def check_verifid(self):
        """ 验证信息 """
        if not (self.is_success and self.usrid > 0):
            self.is_verified = False
            self.reason = self.reason or '行驶证认证失败'
        elif not self.is_support:
            self.is_verified = False
            self.reason = '目前仅支持非营运的小型汽车或新能源车'
        else:
            self.is_verified = True
        self.save(update_fields=['is_verified', 'reason', 'updated_at'])
        return self.is_verified


class VehicleModelManager(models.Manager):
    """ VehicleModel.objects 方法定制 """

    def get_vehicle_model(self, model, vehicle_type=''):
        inst, is_created = self.get_or_create(model=model, defaults=dict(
            vehicle_type=vehicle_type
        ))
        logger.info(f'get_vehicle_model__created {inst.pk} {is_created} {model}')
        if vehicle_type and (not inst.vehicle_type):
            inst.vehicle_type = vehicle_type
            inst.save(update_fields=['vehicle_type', 'updated_at'])
            inst.extra_log('type', type=vehicle_type)
        return inst


class VehicleModel(BasicModel):
    """ 车辆型号信息 """

    class Meta:
        verbose_name = 'VehicleModel'
        verbose_name_plural = verbose_name
        index_together = ['vehicle_type', 'brand', 'series']
        db_table = 'k_ls_vehicle_model'
        ordering = ('-pk',)

    model = models.CharField('型号', max_length=200, unique=True)  # 车辆品牌
    vehicle_type = models.CharField('类型', max_length=100, default='')
    brand = models.CharField('品牌', max_length=100, default='')
    series = models.CharField('系列', max_length=100, default='')
    prices = fields.IntegerRangeField('价格区间(万)', default=(None, None))
    count = models.PositiveIntegerField('数量', default=0)

    objects = VehicleModelManager()

    @property
    def summary(self):
        if any([self.brand, self.series]):
            desc = f'{self.brand}{self.series} ({self.vehicle_type})'
        else:
            desc = self.vehicle_type
        return desc

    @property
    def vehicle_qs(self):
        qs = Vehicle.objects.filter(model_id=self.pk, usrid__gt=0)
        return qs

    def checkout(self):
        self.count = self.vehicle_qs.count()
        self.save(update_fields=['count', 'updated_at'])
