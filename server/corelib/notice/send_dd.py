"""
钉钉报警信息发送
"""
import json
import uuid
import logging
import requests
from sentry_sdk import capture_message, capture_exception

from kubrick.initialize import ENV_PREFIX, IS_PROD_ENV

logger = logging.getLogger('kubrick.notice')
if IS_PROD_ENV:  # 线上报警机器人：自定义关键词：报警
    token = 'f12d504a3f2e7f173cf5a7930a1b384a1aacd79e6490ea4b621bc56900fec5e2'
else:  # 开发测试机器人，自定义关键词：开发测试
    token = 'cab1445ec9392f067fd1751b5498028de601d8c7e59311d766001d28d66f4d85'
webhook = f'https://oapi.dingtalk.com/robot/send?access_token={token}'


def send_dd_msg(msg, at_mobiles=None, is_atall=False) -> tuple:
    """
    发送钉钉机器人消息
    """
    req_uid = uuid.uuid4()
    msg += f'\n=====> {ENV_PREFIX}'
    at_mobiles = at_mobiles if isinstance(at_mobiles, list) else []
    msg_key = IS_PROD_ENV and '报警' or '开发测试'  # 钉钉机器人安全设置依赖（自定义关键词）
    msg = f'【{msg_key}】{msg}'
    content = {
        "msgtype": "text",
        "text": {
            "content": msg
        },
        "at": {
            "atMobiles": at_mobiles,
            "isAtAll": is_atall
        }
    }
    content_str = json.dumps(content, sort_keys=True, ensure_ascii=False)
    logger.info(f'send_dd_msg__params [{req_uid}] {ENV_PREFIX}: {content_str}')
    try:
        result = requests.post(webhook, json=content).json()
    except Exception as exc:
        logger.warning(f'send_dd_msg__error [{req_uid}] {str(exc)}')
        capture_message('send_dd_msg__error', level='warning')
        logger.exception(f'send_dd_msg__error')
        capture_exception(exc)
        return False, f'error {str(exc)}'
    logger.info(f'send_dd_msg__resp {result}')
    msg = result.get('errmsg', '')
    is_succ = msg == 'ok'
    logger.info(f'send_dd_msg__result [{req_uid}] [{is_succ}:{msg}]')
    return is_succ, msg


if __name__ == '__main__':
    send_dd_msg('hello world')
