from django.db import models
from django.core.exceptions import PermissionDenied

from server.constant import mochoice as mc
from server.corelib.dealer import deal_time
from server.djextend.basemodel import BasicModel


class ConfigurationManager(models.Manager):

    @property
    def is_ucoff_switch(self):
        """ 是否用户码及通话关闭 """
        now = deal_time.get_now()
        is_off = self.filter(
            cate=mc.ConfCate.UCOff,
            begin_at__lte=now,
            finish_at__gt=now,
            is_active=True,
        ).exists()
        return is_off


class Configuration(BasicModel):
    """ 系统配置 """

    class Meta:
        verbose_name = 'Configuration'
        verbose_name_plural = verbose_name
        unique_together = ('cate', 'key', 'sort')
        index_together = ['cate', 'sort', 'is_active']
        db_table = 'k_os_configuration'

    id_sequence_start = int(1e5)

    cate = models.CharField('类型', max_length=20, choices=mc.ConfCate.choices)
    key = models.CharField('Key', max_length=50, db_index=True, blank=True, default='')
    value = models.CharField('Value', max_length=200, blank=True, default='')
    sort = models.PositiveSmallIntegerField('排序权重', blank=True, default=0)
    memo = models.CharField('备忘', max_length=100, blank=True, default='')
    begin_at = models.DateTimeField('生效时间', db_index=True)
    finish_at = models.DateTimeField('失效时间', db_index=True)
    is_active = models.BooleanField('是否有效', default=True)

    objects = ConfigurationManager()

    def delete(self, *args, **kwargs):
        raise PermissionDenied
