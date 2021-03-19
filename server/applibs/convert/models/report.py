import logging
from django.db import models
from django.contrib.postgres import fields

from server.constant import mochoice as mc
from server.djextend.basemodel import BasicModel

logger = logging.getLogger('kubrick.debug')


class ReportUserManager(models.Manager):

    def get_report_user(self, touchid):
        """ 获取被举报用户 """
        inst, is_created = self.get_or_create(touchid=touchid)
        logger.info(f'get_report_user__done {touchid} {is_created}')
        return inst


class ReportUser(BasicModel):
    """ 被举报用户 """

    class Meta:
        verbose_name = 'ReportUser'
        verbose_name_plural = verbose_name
        index_together = ['is_disable', 'operator', 'count_user']
        db_table = 'k_rt_reportuser'
        ordering = ('-updated_at',)

    touchid = models.BigIntegerField('用户', primary_key=True)
    is_disable = models.BooleanField('是否禁用', default=False)
    disabled_at = models.DateTimeField('禁用时间', null=True, default=None)
    disable_txt = models.TextField('禁用原因', default='')
    active_txt = models.TextField('解除禁用原因', default='')
    count_report = models.PositiveSmallIntegerField('被举报次数', default=0)
    count_user = models.PositiveSmallIntegerField('被举报用户人数', default=0)
    operator = models.PositiveIntegerField('运营操作员', default=0)

    objects = ReportUserManager()

    @property
    def touch_user(self):
        from server.applibs.account.models import AuthUser
        user = AuthUser.objects.get(pk=self.touchid)
        return user

    def sync_user_active(self, active: bool, operator):
        """ 同步用户状态 """
        self.touch_user.set_active(active, operator)

    def set_disable(self, reason, operator=0):
        """ 禁用用户 """
        self.is_disable, self.operator = True, operator
        self.disable_txt = f'{self.disable_txt}|{operator}:{reason}'
        self.save(update_fields=['is_disable', 'operator', 'disable_txt', 'updated_at'])
        self.extra_log('disable', operator=operator, reason=reason)
        self.sync_user_active(False, operator)

    def set_active(self, reason, operator=0):
        """ 解除禁用 """
        self.is_disable, self.operator = False, operator
        self.active_txt = f'{self.active_txt}|{operator}:{reason}'
        self.save(update_fields=['is_disable', 'operator', 'active_txt', 'updated_at'])
        self.extra_log('active', operator=operator, reason=reason)
        self.sync_user_active(True, operator)

    def check_count(self):
        record_qs = ReportRecord.objects.filter(
            touchid=self.touchid
        )
        self.count_report = record_qs.count()
        self.count_user = record_qs.values('usrid').distinct().count()
        self.save(update_fields=['count_report', 'count_user', 'updated_at'])
        self.auto_disable()

    def auto_disable(self):
        """ 自动禁用，当前规则：超过5个用户举报 """
        if not self.touch_user.is_active:
            return
        if self.count_user < 5:
            return
        from server.corelib.notice.async_tasks import send_dd_msg__task
        reason = '超过5个用户举报自动禁用'
        self.set_disable(reason)
        dd_msg = f'{self.touch_user} 因被举报自动禁用'
        send_dd_msg__task(dd_msg)


class ReportRecordManager(models.Manager):

    def add_report_record(self, usrid, touchid, kind, kind_txt='', is_offend=False, offended='', evidence=None):
        """  添加举报记录 """
        assert kind in mc.ReportKind, f'kind_wrong {kind}'
        evidence = evidence if isinstance(evidence, list) else []
        kind_txt = kind_txt if kind == 0 else mc.REPORT_KIND_DIC.get(kind, kind_txt)
        inst = self.create(
            usrid=usrid,
            touchid=touchid,
            kind=kind,
            kind_txt=kind_txt,
            is_offend=is_offend,
            offended=offended,
            evidence=evidence,
        )
        ReportUser.objects.get_report_user(touchid)
        inst.report_user.check_count()
        return inst


class ReportRecord(BasicModel):
    """ 举报记录 """

    class Meta:
        verbose_name = 'ReportRecord'
        verbose_name_plural = verbose_name
        index_together = ['kind', 'is_offend', 'is_solved']
        db_table = 'k_rt_reportrecord'
        ordering = ('-updated_at',)

    usrid = models.BigIntegerField('用户', db_index=True)
    touchid = models.BigIntegerField('对方', db_index=True)
    kind = models.PositiveSmallIntegerField('类型', choices=mc.ReportKind.choices, default=0)
    kind_txt = models.CharField('类型描述', max_length=50, default='')
    is_offend = models.BooleanField('是否反感', default=False)  # 有人身攻击或让人感觉不适
    offended = models.CharField('反感原因或感受', max_length=200, default='')
    evidence = fields.ArrayField(models.URLField(default=''), verbose_name='证据', size=5)
    is_solved = models.BooleanField('是否已解决', default=False)
    feedback = models.CharField('给举报者的反馈', max_length=200, default='')
    operator = models.PositiveIntegerField('运营操作员', default=0)
    memo = models.TextField('运营备忘', default='')

    objects = ReportRecordManager()

    @property
    def report_user(self):
        user = ReportUser.objects.get(touchid=self.touchid)
        return user
