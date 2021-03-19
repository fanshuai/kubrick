import logging
import datetime
from django.db import models

from server.djextend.basemodel import BasicModel
from server.corelib.dealer import deal_time

logger = logging.getLogger('kubrick.debug')


class BillDetailManager(models.Manager):

    def call_record_add(self, call):
        """ 通话账单添加 """
        from server.applibs.outside.models import CallRecord
        assert isinstance(call, CallRecord), str(call)
        if not (call.call_ts > 0):
            return None
        bill_at = deal_time.time_floor_ts(call.callede_at)
        summary = f'与{call.msg_info.other_remark_name}通话'
        extra = dict(day_index=call.day_index)
        # is_free = call.day_index < 3  # 每天免单两次
        is_free = True  # 因小程序审核，计费功能2020-1105下线
        inst, is_created = self.get_or_create(
            call_id=call.pk,
            defaults=dict(
                usrid=call.usrid,
                amount=call.fee,
                summary=summary,
                bill_at=bill_at,
                is_free=is_free,
                extra=extra,
            )
        )
        logger.info(f'call_record_add__done {inst.usrid} {inst.call_id} {inst.pk} {is_created}')
        inst.checkout()
        return inst

    def call_record_wxpay_done(self, wxpay):
        """ 通话账单支付完成 """
        from server.applibs.billing.models import WXPay
        assert isinstance(wxpay, WXPay) and wxpay.is_done
        try:
            bill = self.get(pk=wxpay.instid, usrid=wxpay.usrid)
        except BillDetail.DoesNotExist:
            logger.warning(f'call_record_wxpay_done__no_bill {wxpay.pk} {wxpay.instid}')
            return None
        bill.is_paid = True
        bill.pay_id = wxpay.pk
        bill.save(update_fields=['is_paid', 'pay_id', 'updated_at'])
        bill.extra_log('paid', pay_id=bill.pay_id)
        return bill

    def get_bill_range_ts(self, usrid):
        """ 用户账单时间戳区间 """
        qs = self.filter(usrid=usrid, is_del=False).order_by('bill_at', 'pk')
        inst_first, inst_last = qs.first(), qs.last()
        ts_first, ts_last = None, None
        if isinstance(inst_first, BillDetail):
            ts_first = deal_time.time_floor_ts(inst_first.bill_at).timestamp()
        if isinstance(inst_last, BillDetail):
            ts_last = deal_time.time_floor_ts(inst_last.bill_at).timestamp()
        return ts_first, ts_last

    def get_bill_unpaid_qs(self, usrid):
        """ 未支付账单 """
        qs = self.filter(
            usrid=usrid, is_del=False,
            is_free=False, is_paid=False,
        ).order_by('-bill_at', '-pk')
        return qs


class BillDetail(BasicModel):
    """ 账单明细 """

    class Meta:
        verbose_name = 'BillDetail'
        verbose_name_plural = verbose_name
        db_table = 'k_bl_bill_detail'
        ordering = ('-bill_at', '-pk')

    usrid = models.BigIntegerField('用户', db_index=True)
    amount = models.PositiveSmallIntegerField('金额', default=0)
    summary = models.CharField('摘要', max_length=120, default='')
    pay_id = models.BigIntegerField('支付记录', db_index=True, default=0)
    bill_at = models.DateTimeField('入账时间', db_index=True, null=True, default=None)
    call_id = models.BigIntegerField('通话记录', unique=True, null=True, default=None)
    month_id = models.IntegerField('月度账单', db_index=True, default=0)
    is_free = models.BooleanField('是否免单', default=False)
    is_paid = models.BooleanField('是否支付', default=False)
    is_del = models.BooleanField('已删除', default=False)

    objects = BillDetailManager()

    @property
    def humanize_at(self):
        """ 易读入账时间 """
        at = deal_time.show_humanize(self.bill_at)
        return at

    def checkout(self):
        """ 月度账单更新 """
        if self.is_del:
            logger.warning(f'bill_detail__checkout_is_del {self.pk}')
            return
        month = deal_time.time_floor_ts(self.bill_at).replace(day=1).date()
        inst = BillMonth.objects.get_user_bill_month(month, self.usrid)
        self.month_id = inst.pk
        up_fields = ['month_id', 'updated_at']
        self.save(update_fields=up_fields)
        inst.checkout()


class BillMonthManager(models.Manager):

    def get_user_bill_month(self, month, usrid):
        assert isinstance(month, datetime.date), type(month).__name__
        assert month.day == 1, month.isoformat()
        inst, is_created = self.get_or_create(month=month, usrid=usrid)
        logger.info(f'get_user_bill_month__done {usrid} {month} {inst.pk} {is_created}')
        return inst


class BillMonth(BasicModel):
    """ 月度账单 """

    class Meta:
        verbose_name = 'BillMonth'
        verbose_name_plural = verbose_name
        unique_together = ('month', 'usrid')
        db_table = 'k_bl_bill_month'
        ordering = ('-month', '-pk')

    month = models.DateField('月份')
    usrid = models.BigIntegerField('用户', db_index=True)
    count = models.PositiveIntegerField('交易量', default=0)
    amount = models.PositiveIntegerField('消费金额', default=0)
    free = models.PositiveIntegerField('免单金额', default=0)

    objects = BillMonthManager()

    @property
    def month_fmt(self):
        fmt = self.month.isoformat()[:7]
        return fmt

    @property
    def detail_qs(self):
        qs = BillDetail.objects.filter(
            month_id=self.pk,
            usrid=self.usrid,
            is_del=False,
        ).order_by('-bill_at', '-pk')
        return qs

    def checkout(self):
        """ 金额更新 """
        self.count = self.detail_qs.count()
        self.amount = self.detail_qs.aggregate(
            amount=models.Sum('amount')
        ).get('amount') or 0
        self.free = self.detail_qs.filter(is_free=True).aggregate(
            amount=models.Sum('amount')
        ).get('amount') or 0
        self.save(update_fields=['free', 'count', 'amount', 'updated_at'])
