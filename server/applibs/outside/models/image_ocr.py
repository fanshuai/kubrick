"""
阿里云 图片OCR识别
https://help.aliyun.com/document_detail/53435.html
https://help.aliyun.com/document_detail/87122.html
https://help.aliyun.com/document_detail/70292.html
"""
import time
import logging
from django.db import models

from server.constant import mochoice as mc
from server.djextend.basemodel import BasicModel, BIDModel
from server.corelib.safety import encrypt_dic, decrypt_dic
from server.third.aliyun.oss import oss_sign_url
from server.third.aliyun.ocr import ocr_query

logger = logging.getLogger('kubrick.debug')


class ImageOcrManager(models.Manager):
    """ ImageOcr.objects 方法定制 """

    def image_ocr_create(self, oss_key, ocr_type, usrid):
        assert isinstance(usrid, int) and usrid > 0, usrid
        assert ocr_type != mc.OCRType.VehicleNum.value, ocr_type
        defaults = dict(usrid=usrid, ocr_type=ocr_type)
        inst, is_created = self.get_or_create(oss_key=oss_key, defaults=defaults)
        if is_created or (inst.is_victor is None):
            inst.do_ocr_query()
        return inst

    def idcard_image_ocr(self, img_front, img_back, usrid):
        """ 实名认证，身份证图片OCR """
        assert isinstance(usrid, int) and usrid > 0, usrid
        front_ocr_type = mc.OCRType.IDCardFront
        back_ocr_type = mc.OCRType.IDCardBack
        # 身份证正面(人像面)照片
        inst_front = self.image_ocr_create(img_front, front_ocr_type, usrid)
        # 身份证背面(国徽面)照片
        inst_back = self.image_ocr_create(img_back, back_ocr_type, usrid)
        front_dic, back_dic = inst_front.result_dic, inst_back.result_dic
        from server.applibs.account.models import IDCard
        is_ok, resp = IDCard.objects.idcard_approve(
            img_front, img_back, front_dic, back_dic, usrid,
        )
        return is_ok, resp


class ImageOcr(BasicModel, BIDModel):
    """ 图片OCR识别记录 """

    class Meta:
        verbose_name = 'ImageOcr'
        verbose_name_plural = verbose_name
        index_together = ['ocr_type', 'suggestion', 'is_victor']
        db_table = 'k_os_image_ocr'
        ordering = ('-pk',)

    oss_key = models.URLField('图片路径', unique=True)
    usrid = models.BigIntegerField('用户', db_index=True, default=0)
    rate = models.DecimalField('置信度', max_digits=5, decimal_places=2, default=0)
    ocr_type = models.PositiveSmallIntegerField('OCR类型', choices=mc.OCRType.choices, default=0)
    suggestion = models.CharField('建议操作', choices=mc.Suggestion.choices, max_length=20, default='')
    ocr_use_ms = models.PositiveSmallIntegerField('OCR耗时', default=0)
    reason = models.CharField('原因', max_length=200, default='')
    is_victor = models.BooleanField('是否成功', null=True, default=None)
    result = models.JSONField('结果', default=dict)  # 加密

    objects = ImageOcrManager()

    @property
    def oss_url(self):
        """ OSS URL，无水印，60秒内有效 """
        url = oss_sign_url(self.oss_key)
        return url

    @property
    def result_dic(self):
        """ 结果解密 """
        dic = decrypt_dic(self.result)
        return dic

    def do_ocr_query(self):
        if self.is_victor:
            logger.info(f'do_ocr_query__is_victor {self.pk}')
            return
        ts_start = int(1000 * time.time())
        result = ocr_query(self.oss_url, str(self.pk), self.ocr_type)
        self.ocr_use_ms = int(1000 * time.time()) - ts_start
        up_fields = ['is_victor', 'ocr_use_ms', 'updated_at']
        if not isinstance(result, dict):
            self.is_victor = False
            self.reason = str(result)
            up_fields.append('reason')
            self.save(update_fields=up_fields)
            logger.warning(f'do_ocr_query__fail {self.pk} {str(result)}')
            return
        self.is_victor = True
        self.rate = result['_rate']
        self.result = encrypt_dic(result)
        self.suggestion = result['_suggestion']
        up_fields.extend(['rate', 'result', 'suggestion'])
        self.save(update_fields=up_fields)
