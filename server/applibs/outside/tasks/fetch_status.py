"""
短信通知发送状态同步
"""
import logging
from kubrick.celery import app

from server.corelib.dealer import deal_time
from server.corelib.notice.async_tasks import send_dd_msg__task
from server.constant.djalias import CQueueAlias

logger = logging.getLogger('kubrick.celery')


@app.task(queue=CQueueAlias.Timed.value)
def fetch_status_smsrecord(now=None):
    """ 短信通知状态检查 """
    from server.constant import mochoice as mc
    from server.applibs.outside.models import SmsRecord
    time_start, time_end = deal_time.every_five_hours(now=now)
    sms_all_qs = SmsRecord.objects.filter(
        created_at__gte=time_start,
        created_at__lt=time_end,
    )
    init_count = sms_all_qs.filter(status=mc.SMSStatus.Init).count()
    sms_qs = sms_all_qs.filter(status=mc.SMSStatus.Waiting)
    waiting_count = sms_qs.count()
    done_count = 0
    for sms in sms_qs:
        sms.query()
        done_count += 1 if sms.is_ else 0
    deal_info = f'{time_start} ~ {time_end}: {done_count}/{waiting_count}'
    logger.info(f'fetch_status_smsrecord__done {deal_info} {init_count}')
    if (done_count != waiting_count) or init_count:
        send_dd_msg__task(f'短信通知状态检查：{deal_info} 未发送：{init_count}')
    result = dict(
        task='fetch_status_smsrecord',
        done=done_count,
        init=init_count,
        waiting=waiting_count,
        end_at=time_end.isoformat(),
        start_at=time_start.isoformat(),
    )
    return result


@app.task(queue=CQueueAlias.Timed.value)
def fetch_status_callrecord(now=None):
    """ 通话状态检查 """
    from server.applibs.outside.models import CallRecord
    time_start, time_end = deal_time.round_floor_ten_mins(now=now)
    call_qs = CallRecord.objects.filter(
        created_at__gte=time_start,
        created_at__lt=time_end,
    )
    all_count = call_qs.count()
    done_count = 0
    end_count = 0
    for call in call_qs:
        if call.is_end:
            end_count += 1
            continue
        call.query_call_ytx()
        done_count += 1 if call.is_end else 0
    init_count = all_count - end_count - done_count
    deal_info = f'{time_start} ~ {time_end}: {end_count}/{done_count}/{all_count}'
    logger.info(f'fetch_status_callrecord__done {deal_info} {init_count}')
    if init_count > 0:
        send_dd_msg__task(f'通话状态检查：{deal_info} 异常状态：{init_count}')
    result = dict(
        task='fetch_status_callrecord',
        all=all_count,
        end=end_count,
        done=done_count,
        init=init_count,
        end_at=time_end.isoformat(),
        start_at=time_start.isoformat(),
    )
    return result
