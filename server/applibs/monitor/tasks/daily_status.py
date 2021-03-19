""" 每日状态状态统计 """
import json
import logging
import datetime
import pendulum
from django.db.models import Count
from collections import OrderedDict

from kubrick.celery import app
from server.constant.normal import TZCN
from server.corelib.dealer import deal_time
from server.corelib.notice.async_tasks import send_dd_msg__task
from server.constant.djalias import CQueueAlias

logger = logging.getLogger('kubrick.celery')


@app.task(queue=CQueueAlias.Timed.value)
def daily_status_count(date=None):
    """ 每日通信状态统计 """
    from server.applibs.account.models import PNVerify
    from server.applibs.outside.models import SmsRecord, CallRecord
    now = deal_time.get_now()
    if not isinstance(date, datetime.date):
        date = now.add(days=-1).date()
    time_start = datetime.datetime.combine(date, datetime.time.min)
    time_start = pendulum.instance(time_start, tz=TZCN)
    time_end = time_start.add(days=1)
    pnv_qs = PNVerify.objects.filter(
        created_at__gte=time_start,
        created_at__lt=time_end,
    ).values_list('status').annotate(
        total=Count('status'),
    ).order_by('total')
    pnv_dic = OrderedDict(pnv_qs)
    sms_qs = SmsRecord.objects.filter(
        created_at__gte=time_start,
        created_at__lt=time_end,
    ).values_list('status').annotate(
        total=Count('status')
    ).order_by('total')
    sms_dic = OrderedDict(sms_qs)
    call_qs = CallRecord.objects.filter(
        created_at__gte=time_start,
        created_at__lt=time_end,
    ).values_list('status').annotate(
        total=Count('status')
    ).order_by('total')
    call_dic = OrderedDict(call_qs)
    dd_msg = f'每日通信统计：'
    dd_msg += f'\n短信验证码：{json.dumps(pnv_dic)}'
    dd_msg += f'\n短信通知：{json.dumps(sms_dic)}'
    dd_msg += f'\n语音通话：{json.dumps(call_dic)}'
    send_dd_msg__task(dd_msg)
    result = dict(
        task='daily_status_count',
        pnv_dic=pnv_dic,
        sms_dic=sms_dic,
        call_dic=call_dic,
        end_at=time_end.isoformat(),
        start_at=time_start.isoformat(),
        now=now.isoformat(),
    )
    return result
