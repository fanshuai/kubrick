"""
阿里云通信回执订阅
    SmsReport: 短信下行回执报告消息
        https://help.aliyun.com/document_detail/101508.html
        https://help.aliyun.com/document_detail/101889.html


# 循环读取删除消息直到队列空
# receive message请求使用long polling方式，通过wait_seconds指定长轮询时间为3秒

# # long polling 解析:
# ## 当队列中有消息时，请求立即返回；
# ## 当队列中没有消息时，请求在MNS服务器端挂3秒钟，在这期间，有消息写入队列，请求会立即返回消息，3秒后，请求返回队列没有消息；
"""
import time
import json
import logging
from abc import ABC
from dataclasses import dataclass
from aliyunsdkcore.acs_exception.exceptions import ServerException
from aliyunsdkdybaseapi.request.v20170525.QueryTokenForMnsQueueRequest import QueryTokenForMnsQueueRequest
from aliyunsdkcore.profile import region_provider
from mns.mns_exception import MNSExceptionBase
from mns.queue import Message, Queue
from mns.account import Account

from server.third.aliyun import acs_client
from server.corelib.dealer.deal_time import get_now, get_tzcn_parse

logger = logging.getLogger('kubrick.notice')

# 云通信固定的endpoint地址
endpoint = 'http://1943695596114318.mns.cn-hangzhou.aliyuncs.com'
region_provider.add_endpoint('Dybaseapi', 'dybaseapi.aliyuncs.com', 'cn-hangzhou')


@dataclass
class QueueConfig:
    """ 队列配置 """
    msg_type: str  # 消息类型
    queue_name: str  # 队列名称
    desc: str  # 回执Token说明


class DYToken(object):
    """ 云通信业务Token存在失效时间，需动态更新。 """

    def __init__(self, q_cfg):
        assert isinstance(q_cfg, QueueConfig)
        self.queue_cfg = q_cfg
        self.tmp_access_id = None
        self.tmp_access_key = None
        self.expire_time = None
        self.token = None

    @property
    def tk_desc(self):
        desc = f'Token {self.queue_cfg.desc} [{self.queue_cfg.msg_type}]'
        return desc

    @property
    def need_refresh(self):
        """ 是否需要刷新 """
        if self.expire_time is None:
            logger.info(f'{self.tk_desc} need_refresh no expire_time')
            return True
        now = get_now()
        expire = get_tzcn_parse(self.expire_time)
        # 失效时间与当前系统时间比较，提前2分钟刷新Token
        if (expire - now).seconds < 120:
            logger.info(f'{self.tk_desc} need_refresh {now} ~ {expire}')
            return True
        return False

    def refresh(self):
        logger.info(f'{self.tk_desc} start refresh token ...')
        request = QueryTokenForMnsQueueRequest()
        request.set_MessageType(self.queue_cfg.msg_type)
        request.set_QueueName(self.queue_cfg.queue_name)
        response = acs_client.do_action_with_exception(request)
        logger.info(f'{self.tk_desc} QueryTokenForMnsQueueRequest response: {response}')
        if response is None:
            raise ServerException('GET_TOKEN_FAIL', f'{self.tk_desc} 获取token时无响应')
        response_body = json.loads(response)
        if response_body.get('Code') != 'OK':
            raise ServerException('GET_TOKEN_FAIL', f'{self.tk_desc} 获取token失败')
        sts_token = response_body.get('MessageTokenDTO')
        self.tmp_access_key = sts_token.get('AccessKeySecret')
        self.tmp_access_id = sts_token.get('AccessKeyId')
        self.expire_time = sts_token.get('ExpireTime')
        self.token = sts_token.get('SecurityToken')
        logger.info(f'{self.tk_desc} finish refresh token')


class MNSBaseReceiptSvc(ABC):
    """ 回执订阅 """

    wait_seconds = 3  # 长轮询时间为3秒
    sleep_seconds = 15  # 3秒后，请求返回队列没有消息，sleep间隔
    # ("InvalidArgument" "The value of numofmessages should between 1 and 16")
    batch_count = 10  # 每次接收数据量

    def __init__(self, q_cfg):
        self.queue_cfg = q_cfg
        self.token = DYToken(q_cfg)
        self.account, self.queue = None, None

    @property
    def svc_name(self):
        name = f'{self.__class__.__doc__} [{self.__class__.__name__}]'
        return name

    def token_and_queue_refresh(self):
        """ Token过期刷新 """
        if not self.token.need_refresh:
            return
        self.token.refresh()
        if self.account:
            self.account.mns_client.close_connection()
        self.account = Account(endpoint, self.token.tmp_access_id, self.token.tmp_access_key, self.token.token)
        self.queue = self.account.get_queue(self.queue_cfg.queue_name)
        logger.info(f'{self.token.tk_desc} account and queue ready')

    def handle(self, dic):
        """ 业务处理 """
        raise NotImplementedError

    def handle_msg(self, recv_msg):
        """ 单个消息处理 """
        assert isinstance(recv_msg, Message)
        body = json.loads(recv_msg.message_body)
        receipt_handle = recv_msg.receipt_handle
        message_id, dequeue_count = recv_msg.message_id, recv_msg.dequeue_count
        logger.info(f'{self.svc_name} Receive Message {message_id} {dequeue_count} {receipt_handle}\n{body}')
        is_ok = self.handle(body)
        return is_ok

    def start_logger(self):
        logger.info(
            f'\n{self.svc_name}\n'
            f'{16 * "="} Receive And Delete Message From Queue {16 * "="}\n'
            f'QueueName: {self.queue_cfg.queue_name}\n'
            f'MessageType: {self.token.tk_desc}\n'
            f'WaitSeconds: {self.wait_seconds}\n'
            f'SleepSeconds: {self.sleep_seconds}\n'
        )

    def run(self):
        self.start_logger()
        while True:
            receipt_handles = []
            try:
                self.token_and_queue_refresh()
                recv_msgs = self.queue.batch_receive_message(self.batch_count, self.wait_seconds)
                for recv_msg in recv_msgs:
                    is_ok = self.handle_msg(recv_msg)
                    if is_ok:  # 处理成功才删除消息
                        receipt_handles.append(recv_msg.receipt_handle)
                    logger.info(f'{self.svc_name} Handle MessageID: {recv_msg.message_id} done {is_ok}')
            except MNSExceptionBase as mns_exc:
                if mns_exc.type == 'QueueNotExist':
                    logger.warning(f'{self.svc_name} Queue not exist, please create queue.')
                    break
                elif mns_exc.type == 'MessageNotExist':
                    logger.info(f'{self.svc_name} Queue is empty! sleep {self.sleep_seconds}s')
                    time.sleep(self.sleep_seconds)
                    continue
                logger.exception(f'{self.svc_name} Receive Message Fail! Exception: {mns_exc}')
                break
            except Exception as exc:
                logger.warning(f'{self.svc_name} error {exc}')
                raise
            logger.info(f'{self.svc_name} Receive Message Count {len(receipt_handles)}')
            if len(receipt_handles) == 0:
                continue
            try:  # 删除消息
                assert isinstance(self.queue, Queue)
                self.queue.batch_delete_message(receipt_handles)
                logger.info(f'{self.svc_name} Delete Message Succeed! ReceiptHandles: {receipt_handles}')
            except MNSExceptionBase as exc:
                logger.warning(f'{self.svc_name} Delete Message Fail! Exception: {exc}')
        raise RuntimeError(f'{self.svc_name} break!')
