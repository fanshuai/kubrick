"""
文本反垃圾
https://help.aliyun.com/document_detail/53436.html
https://help.aliyun.com/document_detail/70439.html
流量包成本：810 / 500000 = 0.00162
"""
import json
import logging
import datetime
import functools
from enum import unique
from collections import OrderedDict
from django.db.models import TextChoices
from aliyunsdkgreen.request.v20180509 import TextScanRequest
from sentry_sdk import capture_message, capture_exception

from server.constant import mochoice as mc
from server.third.aliyun import AliReqAction
from server.corelib.sequence.idshift import generate_name_uuid

logger = logging.getLogger('kubrick.api')


@unique
class TextScanLabel(TextChoices):
    """ 文本垃圾内容检测 """
    normal = 'normal', '正常文本'
    spam = 'spam', '含垃圾信息'
    ad = 'ad', '广告'
    politics = 'politics', '涉政'
    terrorism = 'terrorism', '暴恐'
    abuse = 'abuse', '辱骂'
    porn = 'porn', '色情'
    flood = 'flood', '灌水'
    contraband = 'contraband', '违禁'
    meaningless = 'meaningless', '无意义'
    customized = 'customized', '自定义'


TextScanLabelDic = OrderedDict(TextScanLabel.choices)


def txt_spam_query(text):
    """ 文本反垃圾 """
    data_id = str(generate_name_uuid(text))
    ms = datetime.datetime.now().microsecond
    task = {
        'dataId': data_id,
        'content': text,
        'time': ms,
    }
    params = {
        'tasks': [task],
        'scenes': ['antispam'],
    }
    content = json.dumps(params, sort_keys=True)
    resp = None
    try:
        request = TextScanRequest.TextScanRequest()
        request.set_accept_format('JSON')
        request.set_content(content)
        resp = AliReqAction(request).do_req_action()
        data_info = {row['dataId']: row for row in resp['data']}[data_id]
        code, msg = data_info['code'], data_info['msg']
        if not (code == 200 and msg == 'OK'):
            logger.warning(f'txt_spam_query__fail {data_id} {code} {msg} resp: \n{resp}')
            return '内容检测失败'
        data = data_info['results'][0]
        suggestion = data['suggestion']
        if not (suggestion == mc.Suggestion.Block):
            return ''
        rate = data['rate']
        label = data['label']
        label_desc = TextScanLabelDic[label]
        capture_message('txt_spam_query__hit', level='info')
        logger.warning(f'txt_spam_query__hit {data_id}: [{label}] {label_desc} {rate}')
    except Exception as exc:
        exc_type = type(exc).__name__
        logger.info(f'txt_spam_query__error {data_id} {text} {exc_type} resp: \n{resp}')
        capture_exception(exc)
        logger.exception(exc)
        # 默认通过，为配合缓存
        return ''
    return label_desc


@functools.lru_cache
def txt_spam_cached(txt):
    """ 文本反垃圾，相同内容缓存 """
    if not txt:
        return ''
    desc = txt_spam_query(txt)
    return desc
