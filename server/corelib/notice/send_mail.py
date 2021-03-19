"""
https://dm.console.aliyun.com
https://help.aliyun.com/document_detail/29444.html
"""
import logging
from aliyunsdkcore.request import CommonRequest
from django.core.mail.message import EmailMessage

from server.third.aliyun import AliReqAction
from kubrick.initialize import IS_PROD_ENV, ENV_PREFIX

logger = logging.getLogger('kubrick.notice')


def send_mail_msg(to, subject='', html_body='', text_body='') -> dict:
    """ 发送邮件通知 """
    if not IS_PROD_ENV:
        subject = f'{ENV_PREFIX} {subject}'
    assert isinstance(to, list), to
    to_address = ','.join(to)
    request = CommonRequest()
    request.set_accept_format('json')
    request.set_domain('dm.aliyuncs.com')
    request.set_protocol_type('https')
    request.set_version('2015-11-23')
    request.set_method('POST')
    request.set_action_name('SingleSendMail')
    request.add_query_param('RegionId', "cn-hangzhou")
    request.add_query_param('AccountName', "noreply@notice.ifand.com")
    request.add_query_param('AddressType', "1")
    request.add_query_param('ReplyToAddress', "true")
    request.add_query_param('ReplyAddress', "postmaster@ifand.com")
    request.add_query_param('TagName', "systemssss")
    request.add_query_param('FromAlias', "访道")
    request.add_query_param('ReplyAddressAlias', "PostMaster")
    request.add_query_param('ClickTrace', "1")
    request.add_query_param('Subject', subject)
    request.add_query_param('HtmlBody', html_body)
    request.add_query_param('TextBody', text_body)
    request.add_query_param('ToAddress', to_address)
    resp_dic = AliReqAction(request).do_req_action()
    return resp_dic


def send_mail_msg__file(to, subject='', body='', files=None) -> int:
    """ 发送带文件的邮件 """
    if not IS_PROD_ENV:
        subject = f'{ENV_PREFIX} {subject}'
    assert isinstance(to, list), to
    msg = EmailMessage(
        subject=subject, body=body, to=to,
        reply_to='postmaster@ifand.com',
    )
    files = files if isinstance(files, list) else []
    for one in files:
        msg.attach_file(one)
    num_sent = msg.send()
    logger.info(f'send_mail_msg__file__num_sent {num_sent}')
    return num_sent
