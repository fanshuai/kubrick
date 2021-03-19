"""
MNS短信发送状态回执
SmsReport: 短信下行回执报告消息
https://help.aliyun.com/document_detail/101508.html
https://help.aliyun.com/document_detail/101889.html
"""
import os
import sys
import django
import logging
sys.path.append('./')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'kubrick.settings')
django.setup()
from kubrick.initialize import IS_PROD_ENV
from server.djextend.decorator import auto_close_db, sentry_try
from server.receipt.base import QueueConfig, MNSBaseReceiptSvc
from server.applibs.outside.models import SmsRecord
from server.applibs.account.models import PNVerify

logger = logging.getLogger('kubrick.notice')


class MNSubSmsReportSvc(MNSBaseReceiptSvc):
    """ 下行短信回执订阅 """

    def __init__(self):
        q_cfg = QueueConfig(
            msg_type='SmsReport',
            queue_name='Alicom-Queue-1254358579292780-SmsReport',
            desc='短信下行回执报告消息',
        )
        super().__init__(q_cfg)

    @sentry_try
    @auto_close_db
    def handle(self, dic):
        """ 业务处理 """
        out_id = str(dic['out_id'])
        if out_id.startswith('notice-'):
            dic['tid'] = out_id.replace('notice-', '')
            is_ok = SmsRecord.objects.sms_notice_report_receipt(dic)
        elif out_id.startswith('code-'):
            dic['tid'] = out_id.replace('code-', '')
            is_ok = PNVerify.objects.sms_code_report_receipt(dic)
        else:
            logger.warning(f'{self.svc_name} out_id_wrong {out_id}: {dic}')
            is_ok = True
        return is_ok


def main_single_run():
    """ Docker部署，单进程多实例 """
    assert IS_PROD_ENV, '开发环境启动会消费线上数据！！！'
    svc = MNSubSmsReportSvc()
    logger.info(f'{svc.svc_name} run ...')
    svc.run()


if __name__ == '__main__':
    main_single_run()
