"""
短信发送及查询
https://dysms.console.aliyun.com/dysms.htm
https://help.aliyun.com/document_detail/101347.html
"""
import logging
import phonenumbers
from django.db import models
from django.utils.functional import cached_property
from mirage import fields as mg_fields

from server.constant import mochoice as mc
from server.corelib.hash_id import pk_hashid_decode
from server.djextend.basemodel import BasicModel, BIDModel
from server.corelib.dealer.deal_time import get_tzcn_parse
from server.third.aliyun.dayu import sms_action, sms_constant

logger = logging.getLogger('kubrick.debug')


class SmsRecordManager(models.Manager):

    def sms_send__msg_remind(self, scene, number, params, usrid, touchid, instid):
        """ 发送 消息短信提醒消息 """
        assert scene in sms_constant.SMS_NOTICE_SCENE_MAP, scene
        if self.filter(scene=scene, instid=instid).exists():
            logger.warning(f'sms_send__msg_remind__exists {scene} {instid}')
            return False, f'提醒短信已存在: {scene} {instid}'
        template = sms_constant.SMS_NOTICE_SCENE_MAP[scene]
        sign = sms_constant.SMS_SIGN  # 短信签名
        inst = self.create(
            scene=scene,
            number=number,
            usrid=usrid,
            touchid=touchid,
            sign=sign,
            template=template,
            params=params,
            instid=instid,
        )
        inst.send()
        return True, f'发送成功: {inst.pk}'

    def sms_notice_report_receipt(self, dic):
        """ 通知短信，发送回执MNS订阅 """
        try:
            bid = pk_hashid_decode(dic['tid'])
            inst = self.get(pk=bid, bizid=dic['biz_id'])
            is_ok = inst.report_receipt(dic)
        except (IndexError, SmsRecord.DoesNotExist) as exc:
            logger.warning(f'sms_notice_report_receipt__error {dic} {str(exc)}')
            is_ok = True
        return is_ok


class SmsRecord(BasicModel, BIDModel):
    """ 阿里短信发送记录，仅通知消息，需要关心发送结果 """

    class Meta:
        verbose_name = 'SmsRecord'
        verbose_name_plural = verbose_name
        index_together = ['scene', 'status', 'err_code']
        db_table = 'k_os_sms_record'
        ordering = ('-created_at',)

    scene = models.CharField('场景', choices=mc.SMSNoticeScene.choices, max_length=25)
    number = mg_fields.EncryptedCharField(verbose_name='手机号', max_length=50, db_index=True)  # E164，加密
    usrid = models.BigIntegerField('触发用户', db_index=True, default=0)
    touchid = models.BigIntegerField('触达用户', db_index=True, default=0)
    bizid = models.CharField('回执', db_index=True, max_length=50, default='')  #
    sign = models.CharField('签名', max_length=25, default='')
    template = models.CharField('模板', max_length=50, default='')
    params = models.JSONField('模板参数', default=dict)
    status = models.SmallIntegerField('发送状态', choices=mc.SMSStatus.choices, default=0)
    report_at = models.DateTimeField('收到运营商回执时间', null=True, default=None)
    send_at = models.DateTimeField('转发给运营商时间', null=True, default=None)
    instid = models.BigIntegerField('关联对象', db_index=True, default=0)  # Message、PNVerify
    err_msg = models.CharField('错误信息', max_length=200, default='')
    err_code = models.CharField('错误码', max_length=50, default='')

    objects = SmsRecordManager()

    @property
    def sms_outid(self):
        """ 短信发送外部ID """
        return f'notice-{self.hid}'

    @cached_property
    def parse_info(self):
        info = phonenumbers.parse(self.number, None)
        return info

    @property
    def is_status_final(self):
        """ 是否已终态 """
        is_yes = self.status in [
            mc.SMSStatus.Success,
            mc.SMSStatus.Failure,
        ]
        return is_yes

    @property
    def is_dev_fake(self):
        """ 开发测试，转钉钉通知 """
        is_yes = self.bizid.startswith('dd-mock-')
        return is_yes

    @property
    def national(self):
        """ 国内号码，不带+86 """
        number = str(self.parse_info.national_number)
        return number

    def send(self):
        """ 发送 """
        if self.is_status_final:
            logger.warning(f'sms_send__status_final {self.pk}')
            return self.extra['resp_send']
        resp_dic = sms_action.sms_send__notice(self)
        self.extra['resp_send'] = resp_dic
        self.bizid = resp_dic.get('BizId', '')
        self.status = mc.SMSStatus.Waiting if self.bizid else mc.SMSStatus.Init
        self.save(update_fields=['status', 'bizid', 'extra', 'updated_at'])
        logger.info(f'SmsRecord.send__done {self.pk} {resp_dic}')
        return resp_dic

    def query(self):
        """ 主动查询回执状态 """
        if self.is_status_final and self.report_at:
            logger.info(f'sms_notice_query__final {self.pk}')
            return
        result = sms_action.sms_query__notice(self)
        assert result['OutId'] == self.sms_outid, f'{self.sms_outid} {result}'
        up_fields = ['extra', 'report_at', 'send_at', 'err_code', 'status', 'updated_at']
        self.report_at = get_tzcn_parse(result['ReceiveDate'])  # 短信接收日期和时间 ？！
        self.send_at = get_tzcn_parse(result['SendDate'])  # 短信发送日期和时间 ？！
        self.status = result['SendStatus']
        self.err_code = result['ErrCode']
        self.extra['resp_query'] = result
        self.save(update_fields=up_fields)

    def report_receipt(self, result):
        """ 短信发送回执MNS订阅 """
        self.err_msg = result['err_msg']
        self.err_code = result['err_code']
        self.extra['size'] = result['sms_size']
        self.send_at = get_tzcn_parse(result['send_time'])
        self.report_at = get_tzcn_parse(result['report_time'])
        if self.status in [mc.SMSStatus.Init, mc.SMSStatus.Waiting]:  # 回调时序问题
            self.status = mc.SMSStatus.Success if result['success'] else mc.SMSStatus.Failure
        up_fields = ['err_msg', 'err_code', 'status', 'send_at', 'report_at', 'extra', 'updated_at']
        self.save(update_fields=up_fields)
        return True
