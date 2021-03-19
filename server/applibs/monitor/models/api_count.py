import logging
import pendulum
from django.db import models

from server.djextend.basemodel import BasicModel

logger = logging.getLogger('kubrick.debug')


class APIReqCountManager(models.Manager):
    """ APIReqCount.objects 方法定制 """

    def req_count_increase(self, req_dic):
        trace, usrid = req_dic['trace'], req_dic['usrid']
        now = pendulum.parse(trace['now'])
        assert isinstance(now, pendulum.DateTime)
        inst, is_created = self.get_or_create(
            dt_req=now.date(),
            route=req_dic['route'],
            method=req_dic['method'],
            status=req_dic['status'],
            defaults={},
        )
        if not is_created:
            logger.info(f'req_count_increase__not_created {inst.pk}')
        ms_use = trace['use']
        host = req_dic['host']
        inst.count = models.F('count') + 1
        inst.ms_use = models.F('ms_use') + ms_use
        inst.ct_user = models.F('ct_user') + (1 if usrid else 0)
        inst.hosts[host] = inst.hosts.get(host, 0) + 1
        inst.last = dict(trace=trace, usrid=usrid)
        inst.save(update_fields=['count', 'ct_user', 'ms_use', 'hosts', 'last', 'updated_at'])
        return inst


class APIReqCount(BasicModel):
    """ 请求统计 """
    class Meta:
        verbose_name = 'APIReqCount'
        verbose_name_plural = verbose_name
        unique_together = ('dt_req', 'route', 'method', 'status')
        db_table = 'k_mt_apireq_count'
        ordering = ('-pk',)

    id_sequence_start = int(1e8)

    dt_req = models.DateField('日期', auto_now_add=True)
    route = models.URLField('路由', default='')
    method = models.SlugField('方法', max_length=10, default='')
    status = models.PositiveSmallIntegerField('响应码', default=0)
    count = models.PositiveIntegerField('请求量', default=0)
    ct_user = models.PositiveIntegerField('已登录请求量', default=0)
    ms_use = models.BigIntegerField('请求毫秒数', default=0)
    hosts = models.JSONField('主机', default=dict)
    last = models.JSONField('最后', default=dict)

    objects = APIReqCountManager()

    @property
    def rate_auth(self):
        """ 登录用户比例(%) """
        try:
            desc = '{:.1f}'.format(self.ct_user / self.count * 100)
        except ZeroDivisionError:
            desc = '-'
        return desc

    @property
    def ms_avg(self):
        """ 平均响应时长(ms)，向偶取整 """
        try:
            ms = round(self.ms_use / self.count)
        except ZeroDivisionError:
            ms = 0
        return ms
