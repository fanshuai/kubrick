"""
第三方接口请求统计
"""
import logging
from django.db import models

from server.constant import mochoice as mc
from server.djextend.basemodel import BasicModel
from server.corelib.dealer.deal_time import get_now

logger = logging.getLogger('kubrick.debug')


class CountThirdApiManager(models.Manager):
    """ CountThirdApi.objects 方法定制 """

    def count_thirdapi_increase(self, provider, action, result_type='success', use_ms=0):
        inst, _ = self.get_or_create(
            dt_req=get_now().date(),
            provider=provider,
            action=action,
        )
        up_fields = ['count']
        inst.count = models.F('count') + 1
        field_name = f'ct_{result_type}'
        if not hasattr(inst, field_name):
            logger.warning(f'count_thirdapi_increase__field_error {inst.pk} {field_name}')
            return inst
        up_fields.append(field_name)
        setattr(inst, field_name, models.F(field_name) + 1)
        if result_type == mc.ThirdResultType.Success:
            inst.ms_success = models.F('ms_success') + use_ms
            up_fields.append('ms_success')
        inst.save(update_fields=up_fields)
        return inst


class CountThirdApi(BasicModel):
    """ 第三方请求统计 """
    class Meta:
        verbose_name = 'CountThirdApi'
        verbose_name_plural = verbose_name
        unique_together = ('dt_req', 'provider', 'action')
        db_table = 'k_mt_count_thirdapi'
        ordering = ('-pk',)

    id_sequence_start = int(1e8)

    dt_req = models.DateField('日期', auto_now_add=True)
    provider = models.CharField('服务商', choices=mc.ThirdProvider.choices, max_length=100, default='')
    action = models.URLField('方法', choices=mc.ThirdAction.choices, max_length=100, default='')
    count = models.PositiveIntegerField('请求量', default=0)
    ct_exc = models.PositiveIntegerField('请求异常量', default=0)
    ct_error = models.PositiveIntegerField('返回异常量', default=0)
    ct_failure = models.PositiveIntegerField('返回失败量', default=0)
    ct_success = models.PositiveIntegerField('成功量', default=0)
    ms_success = models.BigIntegerField(default=0)

    objects = CountThirdApiManager()

    @property
    def rate(self):
        """ 成功比例 """
        try:
            desc = '{:.1f} %'.format(self.ct_success / self.count * 100)
        except ZeroDivisionError:
            desc = '-'
        return desc

    @property
    def ms_avg(self):
        """ 成功平均响应时间(ms) """
        if self.ct_success == 0:
            return 0
        return round(self.ms_success / self.ct_success)
