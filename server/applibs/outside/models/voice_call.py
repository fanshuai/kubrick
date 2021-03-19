"""
语音双呼，点击拨号
"""
import math
import logging
import phonenumbers
from django.db import models
from mirage import fields as mg_fields
from django.utils.functional import cached_property
from sentry_sdk import capture_message

from server.constant import mochoice as mc
from server.djextend.basemodel import BasicModel, BIDModel
from server.applibs.convert.tasks import send_wxsm_for_msg_one
from server.voice.ytxz.ytx_const import YTXCallState
from server.corelib.dealer import deal_time
from server.voice.ytxz import ytx_apis

logger = logging.getLogger('kubrick.debug')


class CallRecordManager(models.Manager):

    def get_msg_call(self, msg):
        """ 获取通话记录 """
        from server.applibs.convert.models import Message
        assert isinstance(msg, Message) and msg.is_call
        inst = self.get(msgid=msg.pk, usrid=msg.sender)
        return inst

    def msg_call_phone(self, msg):
        """ 发起双呼通话 """
        from server.applibs.account.models import Phone
        from server.applibs.convert.models import Message
        assert isinstance(msg, Message) and msg.is_call
        usrid, receiver = msg.sender, msg.receiver
        phone_self = Phone.objects.user_phone_main(usrid)
        phone_other = Phone.objects.user_phone_main(receiver)
        inst, is_created = self.get_or_create(
            msgid=msg.pk,
            defaults=dict(
                usrid=phone_self.usrid,
                touchid=phone_other.usrid,
                caller=phone_self.number,
                called=phone_other.number,
            ),
        )
        if not is_created:
            logger.warning(f'msg_call__not_created {msg.pk} {inst.pk}')
            assert inst.touchid == phone_other.usrid, f'{phone_other.usrid}'
            assert inst.usrid == phone_self.usrid, f'{phone_self.usrid}'
            assert inst.called == phone_other.number, f'{phone_other.number}'
            assert inst.caller == phone_self.number, f'{phone_self.number}'
        inst.call_yxt()
        return inst

    def msg_call_query(self, msg):
        """ 查询通话话单 """
        inst = self.get_msg_call(msg)
        inst.query_call_ytx()
        return inst

    def callback_call_ytx(self, result):
        """ 通话话单回调 """
        assert isinstance(result, dict)
        req_id = result['requestid']
        inst = self.get(req_id=req_id)
        inst.callback_call_ytx(result)
        return inst

    def callback_status_ytx(self, result):
        """ 通话状态回调 """
        assert isinstance(result, dict)
        req_id = result['requestid']
        inst = self.get(req_id=req_id)
        inst.callback_status_ytx_up(result)
        return inst


class CallRecord(BasicModel, BIDModel):
    """ 点击拨号 """
    class Meta:
        verbose_name = 'CallRecord'
        verbose_name_plural = verbose_name
        index_together = ['provider', 'status', 'call_state']
        db_table = 'k_os_call_record'
        ordering = ('-created_at',)

    free_limit = 2  # 每天免费通话次数

    msgid = models.BigIntegerField('消息', unique=True)
    usrid = models.BigIntegerField('主叫用户', db_index=True, default=0)
    touchid = models.BigIntegerField('被叫用户', db_index=True, default=0)
    req_id = models.CharField('呼叫ID(供应商)', unique=True, max_length=50, null=True, default=None)
    status = models.SmallIntegerField('呼叫状态', choices=mc.CallStatus.choices, default=0)
    caller = mg_fields.EncryptedCharField(verbose_name='主叫号码', max_length=50, default='')
    called = mg_fields.EncryptedCharField(verbose_name='被叫号码', max_length=50, default='')
    callers_at = models.DateTimeField('主叫接听时间', db_index=True, null=True, default=None)
    callere_at = models.DateTimeField('主叫挂机时间', db_index=True, null=True, default=None)
    calleds_at = models.DateTimeField('被叫接听时间', db_index=True, null=True, default=None)
    callede_at = models.DateTimeField('被叫挂机时间', db_index=True, null=True, default=None)
    status_at = models.DateTimeField('状态同步时间戳', null=True, default=None)
    duration = models.PositiveSmallIntegerField('通话时长(秒)', default=0)  # 32767
    call_state = models.CharField('结果状态', max_length=20, default='')
    provider = models.CharField('服务提供商', max_length=20, default='')
    cost = models.PositiveSmallIntegerField('成本', default=0)
    fee = models.PositiveSmallIntegerField('计费', default=0)
    is_record = models.BooleanField('是否录音', default=False)
    record_file = models.URLField('录音文件', default='')

    objects = CallRecordManager()

    @property
    def callid(self):
        """ 外部ID """
        return self.hid

    @property
    def is_end(self):
        """ 是否终态 """
        is_yes = self.status in [
            mc.CallStatus.ENDCaller,
            mc.CallStatus.ENDCalled,
            mc.CallStatus.ENDOKCall,
        ]
        return is_yes

    @cached_property
    def msg_info(self):
        """ 会话消息 """
        from server.applibs.convert.models import Message
        inst = Message.objects.get(pk=self.msgid, sender=self.usrid)
        return inst

    @property
    def caller_seconds(self):
        """ 主叫接听时长 """
        if not (self.callers_at and self.callere_at):
            return 0
        assert self.callere_at > self.callers_at, self.pk
        seconds = (self.callere_at - self.callers_at).seconds
        return seconds

    @property
    def called_seconds(self):
        """ 被叫接听时长 """
        if not (self.calleds_at and self.callede_at):
            return 0
        assert self.callede_at > self.calleds_at, self.pk
        seconds = (self.callede_at - self.calleds_at).seconds
        return seconds

    @property
    def day_index(self):
        """ 当天第几次有效通话，以通话结束时间过滤 """
        if not self.call_ts:
            return 0
        end_at = deal_time.time_tzcn(self.callede_at)
        start_at = deal_time.time_floor_day(end_at)
        count = self.__class__.objects.filter(
            usrid=self.usrid,
            status=mc.CallStatus.ENDOKCall,
            callede_at__gte=start_at,
            callede_at__lt=end_at,
        ).count()
        return count + 1

    @property
    def call_ts(self):
        """ 有效通话时长 """
        if not (self.status == mc.CallStatus.ENDOKCall):
            return 0
        return self.called_seconds

    @property
    def summary(self):
        """ 呼叫摘要 """
        per = 60  # 分钟秒数
        m, s = self.call_ts // per, self.call_ts % per
        status = self.get_status_display()
        state_desc = str(self.call_state).split('|').pop()
        state_desc = state_desc.replace('正常', '')
        state_desc = state_desc.replace('应答', '')
        state_desc = state_desc.replace('未知', '')
        state_desc = state_desc or '请稍后重试'
        if self.status == mc.CallStatus.ENDOKCall:
            desc = f'{status}，时长：{m}′ {s}″'
        elif self.status == mc.CallStatus.ENDCalled:
            desc = f'{status}：{state_desc}'
        elif self.status == mc.CallStatus.ENDCaller:
            desc = f'{status}：{state_desc}'
        else:
            desc = f'{status}...'
        return desc

    def call_yxt(self):
        """ 云讯，双向呼叫 """
        if self.req_id:
            warn_msg = f'call_yxt__done {self.pk} {self.req_id}'
            capture_message(warn_msg)
            logger.warning(warn_msg)
            return
        src = phonenumbers.parse(self.caller, None).national_number
        dst = phonenumbers.parse(self.called, None).national_number
        try:
            result = ytx_apis.YTXDailBackCallApi(src, dst, self.callid).fetch_result()
            self.req_id, self.provider = result['requestId'], mc.ThirdProvider.YTX
            self.save(update_fields=['req_id', 'provider', 'updated_at'])
        except Exception as exc:
            # {'statusCode': '-104', 'statusMsg': '请求频率过高'}
            self.call_state = str(exc)
            self.status = mc.CallStatus.ENDCaller
            self.save(update_fields=['status', 'call_state', 'updated_at'])
            self.msg_info.up_call_reach(self.status, self.summary)  # 更新触达状态，发起失败

    def query_call_ytx(self):
        """ 云讯，话单获取 """
        if not (self.req_id and (self.provider == mc.ThirdProvider.YTX)):
            warn_msg = f'query_ytx__info_error {self.pk} {self.provider}'
            capture_message(warn_msg)
            logger.warning(warn_msg)
            return
        now = deal_time.get_now()
        created_at = deal_time.time_floor_ts(self.created_at)
        cut_seconds = (now - created_at).seconds
        if cut_seconds < 20:
            logger.warning(f'query_ytx__too_early {self.pk} {cut_seconds}')
            return  # 查询太早没有结果
        result = ytx_apis.YTXCallCdrByResIdOneApi(
            lastresid=self.req_id
        ).fetch_result()
        if not isinstance(result, dict):
            return  # 无查询结果
        self.call_result_ytx_up(result, action='query')

    def callback_call_ytx(self, result):
        """ 云讯，话单回调 """
        if self.provider != mc.ThirdProvider.YTX:
            logger.warning(f'callback_ytx__provider_error {self.pk} {result}')
            return
        if self.req_id != result['requestid']:
            logger.warning(f'callback_ytx__req_id_error {self.pk} {result}')
            return
        self.call_result_ytx_up(result, action='callback')

    def call_result_ytx_up(self, result, action='query'):
        """ 云讯，话单更新 """
        key = f'{self.pk} {action} {self.req_id}'
        assert self.provider == mc.ThirdProvider.YTX, f'{key}: {result}'
        assert self.req_id == result['requestid'], f'{key}: {result}'
        self.duration = result['duration']
        self.call_state = result['stateDesc']
        self.cost = int(100 * result['oriamount'])
        self.callers_at = deal_time.get_tzcn_parse(result['callerstime'])
        self.callere_at = deal_time.get_tzcn_parse(result['calleretime'])
        self.calleds_at = deal_time.get_tzcn_parse(result['calledstime'])
        self.callede_at = deal_time.get_tzcn_parse(result['calledetime'])
        self.save(update_fields=[
            'callers_at', 'callere_at', 'calleds_at', 'callede_at',
            'call_state', 'duration', 'cost', 'updated_at',
        ])
        self.extra_log(f'result-{action}', result=result)
        self.final_status_check()
        self.checkout()

    def final_status_check(self):
        """ 话单更新后，确认通话最终状态 """
        old_status = self.status
        if self.caller_seconds and self.called_seconds:
            new_status = mc.CallStatus.ENDOKCall
        elif self.caller_seconds:
            new_status = mc.CallStatus.ENDCalled
        else:
            new_status = mc.CallStatus.ENDCaller
        self.status = new_status
        self.save(update_fields=['status', 'updated_at'])
        self.extra_log('status-check', status=self.status)
        if self.status == mc.CallStatus.ENDCalled:  # 暂未接通
            task = send_wxsm_for_msg_one.delay(self.msgid)
            logger.info(f'send_wxsm_for_msg_one__task {self.pk} {self.msgid} {task}')
        elif self.status == mc.CallStatus.ENDOKCall:  # 通话结束
            self.mark_msg_read()  # 消息更新已读
        self.msg_info.up_call_reach(self.status, self.summary)  # 更新触达状态，终态
        logger.warning(f'final_status_check__up {self.pk} {old_status} > {self.status}')

    def callback_status_ytx_up(self, result):
        """ 云讯回调，呼叫状态同步 """
        if self.is_end:
            self.extra_log('status-callback-end', result=result)
            logger.warning(f'cb_status_ytx__end {self.pk} {self.status} {result}')
            return
        state_desc = result['stateDesc']
        phone, state = result['dsc'], result['state']
        status_at = deal_time.get_tzcn_parse(result['timestamp'])
        if self.status_at and status_at and (self.status_at > status_at):
            later_info = f'{self.pk} {self.status} {self.status_at} {result}'
            logger.warning(f'callback_status_ytx_up__time_later {later_info}')
        elif status_at:
            self.status_at = status_at
        if str(self.caller).endswith(phone):  # 主叫
            if state in [YTXCallState.Callout, YTXCallState.Alerting]:  # 呼叫主叫...
                self.status = mc.CallStatus.OUTCaller
            elif state == YTXCallState.Answer:  # 主叫接听
                self.status = mc.CallStatus.OUTCalled
            elif state == YTXCallState.Disconnect:
                if self.status == mc.CallStatus.OUTCaller:  # 主叫未接听挂断
                    self.status = mc.CallStatus.ENDCaller
        elif str(self.called).endswith(phone):  # 被叫
            if state in [YTXCallState.Callout, YTXCallState.Alerting]:  # 呼叫被叫...
                if self.status != mc.CallStatus.OUTCalled:
                    self.status = mc.CallStatus.OUTCalled
            elif state == YTXCallState.Answer:  # 被叫接听
                self.status = mc.CallStatus.ONCalling
            elif state == YTXCallState.Disconnect:
                if self.status == mc.CallStatus.OUTCalled:  # 被叫未接听挂断
                    self.status = mc.CallStatus.ENDCalled
        else:
            logger.warning(f'callback_status_ytx_up__phone_error {self.pk} {result}')
        if self.is_end and not self.call_state:
            self.call_state = state_desc  # 话单消息可能先到达
        self.save(update_fields=['status', 'status_at', 'call_state', 'updated_at'])
        self.extra_log('status-callback', status=self.status, result=result)
        self.msg_info.up_call_reach(self.status, self.summary)  # 更新触达状态

    def checkout(self):
        """ 用户费用计算，每天两次免费通话，超次0.2元/分钟 """
        from server.applibs.billing.models import BillDetail
        if not (self.call_ts > 0):
            return
        self.fee = int(20 * math.ceil(self.call_ts / 60))
        self.save(update_fields=['fee', 'updated_at'])
        bill = BillDetail.objects.call_record_add(self)
        if not bill:
            return
        if bill.is_free or bill.is_paid:
            return
        # RTM推送通话账单 # 因小程序审核，计费功能2020-1105下线
        # self.msg_info.rtm_event_bill_reach(bill.hid)
        logger.info(f'rtm_event_bill_reach__offline {bill.pk}')

    def mark_msg_read(self):
        if self.status != mc.CallStatus.ENDOKCall:
            return
        if not self.callede_at:
            return
        self.msg_info.mark_read(self.touchid, self.callede_at)
        self.msg_info.conv_info.check_unread()
