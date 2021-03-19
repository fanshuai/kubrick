"""
通话状态回执
VoiceRecordReport: 订阅录音记录消息
https://help.aliyun.com/document_detail/112507.html
"""
import os
import sys
import django
import logging
sys.path.append('./')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kubrick.settings')
django.setup()
from server.djextend.decorator import auto_close_db, sentry_try
from server.receipt.base import QueueConfig, MNSBaseReceiptSvc

logger = logging.getLogger('kubrick.notice')


class MNSubVoiceRecordReportSvc(MNSBaseReceiptSvc):
    """ 订阅录音记录 """

    def __init__(self):
        q_cfg = QueueConfig(
            msg_type='VoiceRecordReport',
            queue_name='Alicom-Queue-TODO-VoiceRecordReport',  # TODO
            desc='订阅录音记录消息',
        )
        super().__init__(q_cfg)

    @sentry_try
    @auto_close_db
    def handle(self, dic):
        """ 业务处理 """
        return False


def main_single_run():
    """ Docker部署，单进程多实例 """
    svc = MNSubVoiceRecordReportSvc()
    logger.info(f'{svc.svc_name} run ...')
    svc.run()


if __name__ == '__main__':
    main_single_run()
