"""
图片扫描识别
"""
import time
import logging
from dataclasses import asdict

from django.db import models
from django.utils.functional import cached_property
from sentry_sdk import capture_exception

from server.constant import mochoice as mc
from server.third.aliyun.oss import oss_sign_url
from server.third.aliyun.ocr import ocr_query_scan
from server.corelib.dealer.deal_zbar import zbar_scan_by_url
from server.applibs.outside.logic.scan_query import get_scan_qrcode_query, get_ocr_vehicle_query
from server.djextend.basemodel import BasicModel, BIDModel
from server.applibs.convert.logic import trigger_conv

logger = logging.getLogger('kubrick.debug')


class ImageScanManager(models.Manager):
    """ ImageScan.objects 方法定制 """

    def image_scan_create(self, oss_key, usrid, location=None):
        assert isinstance(usrid, int) and usrid > 0, usrid
        location = location if isinstance(location, dict) else {}
        inst = self.create(oss_key=oss_key, usrid=usrid, location=location)
        inst.scan_mode_loop()
        inst.conv_trigger()
        return inst


class ImageScan(BasicModel, BIDModel):
    """ 图片扫描记录 """

    class Meta:
        verbose_name = 'ImageScan'
        verbose_name_plural = verbose_name
        index_together = ['mode', 'is_valid']
        db_table = 'k_os_image_scan'
        ordering = ('-pk',)

    oss_key = models.URLField('图片路径', default='')
    usrid = models.BigIntegerField('用户', db_index=True, default=0)
    mode = models.PositiveSmallIntegerField('模式', choices=mc.ScanMode.choices, default=0)
    convid = models.UUIDField('会话', db_index=True, null=True, default=None)
    reason = models.CharField('原因', max_length=200, default='')
    use_ms = models.PositiveSmallIntegerField('耗时', default=0)
    is_valid = models.BooleanField('是否有效', default=False)
    location = models.JSONField('位置信息', default=dict)
    result = models.JSONField('结果', default=dict)

    objects = ImageScanManager()

    @property
    def oss_url(self):
        """ OSS URL，无水印，10天有效 """
        url = oss_sign_url(self.oss_key)
        return url

    @property
    def is_mode_init(self):
        is_init = self.mode == mc.ScanMode.Init
        return is_init

    @cached_property
    def contact_info(self):
        """ 联系人信息 """
        if not self.convid:
            return None
        from server.applibs.convert.models import Contact
        contact = Contact.objects.get(convid=self.convid, usrid=self.usrid)
        return contact

    def check_qrcode(self, codes):
        """ 二维码内容检查 """
        if not (isinstance(codes, list) and len(codes) > 0):
            return False
        effective_qrcode = False
        self.extra_log('qrcode', qrcode=codes)
        result = get_scan_qrcode_query(codes)
        if result.is_ok:
            mode = mc.ScanMode.ByQRCode.value
            self.mode = mode
            self.result = asdict(result)
            up_fields = ['mode', 'result', 'updated_at']
            self.save(update_fields=up_fields)
            effective_qrcode = True
        else:
            self.reason = result.reason
            self.save(update_fields=['reason', 'updated_at'])
        return effective_qrcode

    def scan_mode_with_zbar(self):
        """ Zbar二维码识别，不准，需OCR backup """
        if not self.is_mode_init:
            return False
        codes = zbar_scan_by_url(self.oss_url)
        return self.check_qrcode(codes)

    def scan_mode_with_ocr(self):
        """ OCR识别，车牌号及二维码 """
        if not self.is_mode_init:
            return False
        res_qr, res_ocr = ocr_query_scan(self.oss_url, str(self.pk))
        if self.check_qrcode(res_qr):
            return True
        if not res_ocr:
            return False
        vehicle_num = res_ocr['num']
        vehicle_type = res_ocr['vehicleType']
        result = get_ocr_vehicle_query(vehicle_type, vehicle_num)
        mode = mc.ScanMode.ByOCRVehicle
        self.mode, self.result = mode, result
        up_fields = ['mode', 'result', 'updated_at']
        self.save(update_fields=up_fields)
        self.extra_log('vehicle', num=vehicle_num, type=vehicle_type)
        return True

    def scan_mode_loop(self):
        """ 尝试所有识别方式 """
        ts_begin = round(time.time() * 1000)
        for func in (
            self.scan_mode_with_zbar,
            self.scan_mode_with_ocr,
        ):
            func_desc = func.__doc__.strip()
            try:
                is_ok = func()
            except Exception as exc:
                logger.warning(f'{func_desc} 异常: {str(exc)}')
                capture_exception(exc)
                logger.exception(exc)
                continue
            if is_ok:
                logger.info(f'scan_mode_loop__success {self.pk} {func_desc}')
                break
        if self.is_mode_init:
            self.reason = self.reason or '无有效信息'
            self.mode = mc.ScanMode.Unrecognized
        else:
            self.is_valid = True
        self.use_ms = round(time.time() * 1000) - ts_begin
        up_fields = ['reason', 'mode', 'is_valid', 'use_ms', 'updated_at']
        self.save(update_fields=up_fields)

    @property
    def beable_vehicle(self):
        """ OCR未注册车辆，客户端引导注册 """
        trigger = self.result.get('trigger')
        if not trigger == mc.TriggerType.OCR:
            return False
        if self.result['type'] not in mc.VehicleTypeSupport:
            return False
        beable = self.get_vehicle() is None
        return beable

    def get_vehicle(self):
        """ 根据OCR信息，获取车辆 """
        trigger = self.result.get('trigger')
        if not trigger == mc.TriggerType.OCR:
            return None
        from server.applibs.release.models import Vehicle
        try:
            veh_type, veh_num = self.result['type'], self.result['num']
            vehicle = Vehicle.objects.get(vehicle_type=veh_type, vehicle_num=veh_num)
        except (KeyError, Vehicle.DoesNotExist):
            return None
        return vehicle

    def conv_by_ocr(self):
        """ 触发会话，车牌号识别 """
        vehicle = self.get_vehicle()
        is_ok, resp = trigger_conv.trigger_conv_by_ocr(
            self.usrid, self.result, vehicle, location=self.location
        )
        return is_ok, resp

    def conv_by_symbol(self):
        """ 触发会话，扫场景码 """
        is_ok, resp = trigger_conv.trigger_conv_by_symbol(
            self.usrid, self.result, location=self.location
        )
        return is_ok, resp

    def conv_by_usercode(self):
        """ 触发会话，扫用户码 """
        is_ok, resp = trigger_conv.trigger_conv_by_usercode(
            self.usrid, self.result, location=self.location
        )
        return is_ok, resp

    def conv_trigger(self):
        """ 触发会话 """
        from server.applibs.convert.models import Contact
        trigger = self.result.get('trigger')
        func_dic = {
            mc.TriggerType.OCR: self.conv_by_ocr,
            mc.TriggerType.Symbol: self.conv_by_symbol,
            mc.TriggerType.UserCode: self.conv_by_usercode,
        }
        func = func_dic.get(trigger)
        up_fields = ['updated_at']
        if self.is_valid and callable(func):
            is_ok, resp = func()
        else:
            is_ok = False
            resp = self.reason or '无法识别'
        if is_ok:
            assert isinstance(resp, Contact)
            self.convid = resp.convid
            up_fields.append('convid')
        else:
            self.reason = resp
            up_fields.append('reason')
        self.save(update_fields=up_fields)
        return is_ok, resp
