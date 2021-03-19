"""
https://dysms.console.aliyun.com/dysms.htm
"""
import json
import random
import logging
import phonenumbers
from aliyunsdkcore.request import CommonRequest

from kubrick.initialize import IS_DEV_ENV
from server.constant import mochoice as mc
from server.third.aliyun import AliReqAction
from server.corelib.dealer.deal_string import filter_emoji
from server.third.aliyun.dayu import sms_mock_content, sms_constant
from server.corelib.dealer.deal_time import time_floor_ts, get_tzcn_format

logger = logging.getLogger('kubrick.notice')


def sms_send(template, params, phone, out_id, sign='') -> dict:
    """ 短信发送 """
    assert isinstance(params, dict)
    sign = sign or sms_constant.SMS_SIGN
    national = phonenumbers.parse(phone, None).national_number
    if IS_DEV_ENV:
        from server.corelib.notice.async_tasks import send_dd_msg__task
        content = sms_mock_content(template, params)
        msg = f'模拟短信发送：{national}\n{content}'
        result = send_dd_msg__task(msg)
        mock_resp = {
            'Message': 'OK',
            'RequestId': f'dd-mock-RequestId-{out_id}',
            'BizId': f'dd-mock-BizId-{out_id}',
            'memo': 'dd-dev-mock',
            'result': result,
            'Code': 'OK',
        }
        logger.info(f'sms_send__dd_mock_resp: {mock_resp}')
        return mock_resp
    tpl_param = json.dumps(params, sort_keys=True)
    request = CommonRequest()
    request.set_accept_format('json')
    request.set_domain('dysmsapi.aliyuncs.com')
    request.set_protocol_type('https')
    request.set_version('2017-05-25')
    request.set_method('POST')
    request.set_action_name('SendSms')
    request.add_query_param('RegionId', 'cn-hangzhou')
    request.add_query_param('SignName', sign)  # 签名
    request.add_query_param('PhoneNumbers', national)  # 手机号
    request.add_query_param('TemplateCode', template)  # 短信模板
    request.add_query_param('TemplateParam', tpl_param)  # 模板参数
    request.add_query_param('OutId', out_id)  # 外部流水扩展字段
    resp_dic = AliReqAction(request).do_req_action()
    return resp_dic


def sms_send__code(pnv, code) -> dict:
    """ 验证码 (0.045元/条) """
    from server.applibs.account.models import PNVerify
    assert isinstance(pnv, PNVerify), f'{str(type(pnv))} {pnv}'
    resp_dic = sms_send(pnv.template, dict(code=code), pnv.number, pnv.sms_outid, sign=pnv.sign)
    return resp_dic


def sms_send__notice(sms) -> dict:
    """ 短信通知 (0.045元/条) """
    from server.applibs.outside.models import SmsRecord
    assert isinstance(sms, SmsRecord), f'{str(type(sms))} {sms}'
    params = {k: filter_emoji(v) for k, v in sms.params.items()}  # 过滤短信参数非法字符
    resp_dic = sms_send(sms.template, params, sms.number, sms.sms_outid, sign=sms.sign)
    return resp_dic


def sms_query(send_at, phone, bizid, out_id) -> dict:
    """ 短信结果 """
    national = phonenumbers.parse(phone, None).national_number
    send_date = time_floor_ts(send_at).format('YYYYMMDD')
    is_dev_fake = bizid.startswith('dd-mock-')
    if is_dev_fake:
        mock_status = random.randint(mc.SMSStatus.Waiting, mc.SMSStatus.Success)
        error_code = 'DELIVERED' if mock_status == mc.SMSStatus.Success else f'mock-{mock_status}'
        result = {
            'OutId': out_id,
            'SendDate': get_tzcn_format(send_at),
            'SendStatus': 3,
            'ReceiveDate': get_tzcn_format(send_at),
            'ErrCode': error_code,
            'TemplateCode': 'dev-mock-TemplateCode',
            'Content': 'dev-mock-Content',
            'PhoneNum': 'dev-mock-PhoneNum',
        }
        return result
    request = CommonRequest()
    request.set_accept_format('json')
    request.set_domain('dysmsapi.aliyuncs.com')
    request.set_protocol_type('https')
    request.set_version('2017-05-25')
    request.set_method('POST')
    request.set_action_name('QuerySendDetails')
    request.add_query_param('RegionId', 'cn-hangzhou')
    request.add_query_param('CurrentPage', 1)  # 当前页码
    request.add_query_param('PageSize', 10)  # 每页显示 1~50
    request.add_query_param('PhoneNumber', national)  # 手机号码
    request.add_query_param('SendDate', send_date)  # 发送日期
    request.add_query_param('BizId', bizid)  # 发送回执ID
    resp_dic = AliReqAction(request).do_req_action()
    results = resp_dic['SmsSendDetailDTOs']['SmsSendDetailDTO']
    result = {row['OutId']: row for row in results}[out_id]
    return result


def sms_query__code(pnv) -> dict:
    """ 验证码 发送结果 """
    from server.applibs.account.models import PNVerify
    assert isinstance(pnv, PNVerify), f'{str(type(pnv))} {pnv}'
    result = sms_query(pnv.captcha_at, pnv.number, pnv.bizid, pnv.sms_outid)
    return result


def sms_query__notice(sms) -> dict:
    """ 短信结果 发送结果 """
    from server.applibs.outside.models import SmsRecord
    assert isinstance(sms, SmsRecord), f'{str(type(sms))} {sms}'
    from server.applibs.outside.models import SmsRecord
    assert isinstance(sms, SmsRecord), f'{str(type(sms))} {sms}'
    result = sms_query(sms.created_at, sms.number, sms.bizid, sms.sms_outid)
    return result
