"""
验证码发送状态同步
"""
import logging
from kubrick.celery import app

from server.corelib.dealer import deal_time
from server.corelib.notice.async_tasks import send_dd_msg__task
from server.constant.djalias import CQueueAlias

logger = logging.getLogger('kubrick.celery')


@app.task(queue=CQueueAlias.Timed.value)
def fetch_status_pnverify(now=None):
    """ 短信验证码状态检查 """
    from server.constant import mochoice as mc
    from server.applibs.account.models import PNVerify
    time_start, time_end = deal_time.round_floor_ten_mins(now=now)
    pnv_qs = PNVerify.objects.filter(
        status=mc.SMSStatus.Waiting,
        created_at__gte=time_start,
        created_at__lt=time_end,
    )
    done_count = 0
    waiting_count = pnv_qs.count()
    for pnv in pnv_qs:
        pnv.sms_code_query()
        done_count += 1 if pnv.is_status_final else 0
    done_info = f'{time_start} ~ {time_end}: {done_count}/{waiting_count}'
    logger.info(f'fetch_status_pnverify__done {done_info}')
    if done_count != waiting_count:
        send_dd_msg__task(f'短信验证码状态检查：{done_info}')
    result = dict(
        task='fetch_status_pnverify',
        done=done_count,
        waiting=waiting_count,
        end_at=time_end.isoformat(),
        start_at=time_start.isoformat(),
    )
    return result
