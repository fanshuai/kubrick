import logging
import pendulum
from django.db import models
from sentry_sdk import capture_exception

from server.constant.normal import TZCN
from server.constant import mochoice as mc
from kubrick.initialize import IS_PROD_ENV, RUN_ENV
from server.djextend.basemodel import BasicModel, BIDModel
from server.third.wechat import wx_pay

logger = logging.getLogger('kubrick.debug')


class WXPayManager(models.Manager):

    def add_unifiedorder(self, usrid, openid, amount, pay_type, body='', instid=0):
        """ 微信支付，统一下单 """
        assert pay_type in mc.PayType, f'pay_type: {pay_type}'
        inst = self.create(
            usrid=usrid, openid=openid, amount=amount,
            status=mc.PayStatus.Init.value,
            pay_type=pay_type, body=body,
            instid=instid,
        )
        inst.init_trade_no()
        inst.launch_unified()
        return inst

    def add_charge_unifiedorder(self, usrid, openid, amount):
        """ 充值，统一下单 """
        pay_type = mc.PayType.Charge.value
        inst = self.add_unifiedorder(usrid, openid, amount, pay_type, body='充值')
        return inst

    def add_paycall_unifiedorder(self, usrid, openid, amount, instid):
        """ 通话账单支付，统一下单 """
        pay_type = mc.PayType.PayCall.value
        inst = self.add_unifiedorder(usrid, openid, amount, pay_type, body='通话', instid=instid)
        return inst

    def callback_result(self, result):
        """ 支付回调 """
        assert isinstance(result, dict)
        trade_no = result['out_trade_no']
        inst = self.get(trade_no=trade_no)
        inst.callback_order(result)


class WXPay(BasicModel, BIDModel):
    """ 微信支付 """

    class Meta:
        verbose_name = 'WXPay'
        verbose_name_plural = verbose_name
        db_table = 'k_bl_wxpay'

    usrid = models.BigIntegerField('用户', db_index=True)
    amount = models.PositiveIntegerField('金额', default=0)
    body = models.CharField('商品描述', max_length=50, db_index=True, default='')
    openid = models.CharField('微信小程序用户标识', db_index=True, max_length=50, default='')
    trade_no = models.CharField('商户订单号', max_length=50, unique=True, null=True, default=None)
    pay_type = models.PositiveSmallIntegerField('类型', choices=mc.PayType.choices, default=0)
    status = models.PositiveSmallIntegerField('状态', choices=mc.PayStatus.choices, default=0)
    transaction = models.CharField('微信订单号', db_index=True, max_length=50, default='')
    prepay_id = models.CharField('微信预支付ID', db_index=True, max_length=50, default='')
    trade_at = models.DateTimeField('交易成功时间', null=True, default=None)
    instid = models.BigIntegerField('关联记录', db_index=True, default=0)

    objects = WXPayManager()

    @property
    def is_final(self):
        """ 是否已终态 """
        is_yes = self.status in [
            mc.PayStatus.Off.value,
            mc.PayStatus.Done.value,
            mc.PayStatus.Fail.value,
        ]
        return is_yes

    @property
    def is_init(self):
        """ 待支付 """
        is_yes = self.status == mc.PayStatus.Init.value
        return is_yes

    @property
    def is_done(self):
        """ 支付成功 """
        is_yes = self.status == mc.PayStatus.Done.value
        return is_yes

    @property
    def is_fail(self):
        """ 支付失败 """
        is_yes = self.status == mc.PayStatus.Fail.value
        return is_yes

    @property
    def is_off(self):
        """ 支付关闭 """
        is_yes = self.status == mc.PayStatus.Off.value
        return is_yes

    @property
    def is_paycall(self):
        """ 通话账单支付交易 """
        is_ok = self.pay_type == mc.PayType.PayCall.value
        return is_ok

    @property
    def jsapi_params(self):
        if not self.prepay_id:
            return None
        params = wx_pay.get_jsapi_params(self.prepay_id)
        return params

    def init_trade_no(self):
        if self.trade_no:
            return
        key = 'WP' if IS_PROD_ENV else f'WP-{RUN_ENV}'
        self.trade_no = f'{key}-{self.hid}'
        self.save(update_fields=['trade_no'])

    def launch_unified(self):
        """ 发起统一下单 """
        try:
            resp_dic = wx_pay.create_unifiedorder(
                self.openid, self.amount, self.trade_no,
                body=self.get_pay_type_display(),
            )
        except Exception as exc:
            logger.exception(exc)
            self.status = mc.PayStatus.Off.value
            self.save(update_fields=['status', 'updated_at'])
            self.extra_log('launch-exc', exc=str(exc))
            self.trade_status_update()
            capture_exception(exc)
            return
        self.prepay_id = resp_dic['prepay_id']
        self.save(update_fields=['prepay_id', 'updated_at'])

    def pay_success(self, action, result):
        """ 支付成功状态更新 """
        if self.is_done:
            logger.warning(f'pay_success__done {self.pk}')
            return
        time_end = result['time_end']
        trade_at = pendulum.parse(time_end, tz=TZCN, strict=False)
        self.status = mc.PayStatus.Done.value
        self.trade_at = self.trade_at or trade_at
        self.transaction = result['transaction_id']
        self.extra[f'result-success-{action}'] = result
        self.save(update_fields=['extra', 'status', 'transaction', 'trade_at', 'updated_at'])
        self.extra_log('pay-success', action=action)
        self.trade_status_update()

    def query_order(self):
        """ 查询支付结果 """
        if self.is_final:   # 已终态
            logger.warning(f'query_order__final {self.pk} {self.status}')
            return
        try:
            result = wx_pay.get_orderquery(self.trade_no)
        except Exception as exc:
            self.extra_log('query-exc', exc=str(exc))
            logger.warning(f'query_order__exc {self.pk} {self.status}')
            capture_exception(exc)
            logger.exception(exc)
            return
        trade_state = result['trade_state']
        self.extra_log('query-trade', state=trade_state)
        if trade_state == 'SUCCESS':  # 支付成功
            self.pay_success('callback', result)
        elif trade_state in wx_pay.FAIL_STATES:  # 明确失败
            up_fields = ['status', 'updated_at']
            self.status = mc.PayStatus.Fail.value
            self.save(update_fields=up_fields)
            self.trade_status_update()
        logger.info(f'query_order__done {self.pk} {self.status}')

    def callback_order(self, result):
        """ 支付结果回调 """
        result_code = result['result_code']
        self.extra_log('callback-result', state=result_code)
        if result_code == 'SUCCESS':  # 支付成功
            self.pay_success('callback', result)
        else:
            self.query_order()  # 重新查询结果
        logger.info(f'callback_order__done {self.pk} {self.status}')

    def trade_status_update(self):
        """ 相关业务状态更新 """
        if self.is_paycall and self.is_done:
            from server.applibs.billing.models import BillDetail
            BillDetail.objects.call_record_wxpay_done(self)
        logger.info(f'trade_status_update__done {self.pk}')
