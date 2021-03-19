"""
发送提醒：微信订阅消息及短信
"""
import logging
import pendulum
from kubrick.celery import app
from kubrick.initialize import IS_PROD_ENV
from server.constant import mochoice as mc
from server.corelib.dealer import deal_time
from server.constant.djalias import CQueueAlias
from server.applibs.account.logic.get_cached import mpa_user_openid
from server.corelib.dealer.deal_string import filter_emoji
from server.djextend.decorator import retry
from server.third.wechat import wx_apis

logger = logging.getLogger('kubrick.celery')


@retry(retries=3)
def wxsm_request(msg, page, data: dict):
    """ 微信订阅消息 生成参数 """
    from server.applibs.convert.models import Message
    assert isinstance(msg, Message)
    tplid = mc.WXSMTID_MAP[msg.msg_type]
    to_openid = mpa_user_openid(msg.receiver)
    mpa_state = 'formal' if IS_PROD_ENV else 'developer'  # trial
    data = {k: dict(value=v) for k, v in data.items()}
    params_dic = dict(
        touser=to_openid,
        template_id=tplid,
        miniprogram_state=mpa_state,
        lang='zh_CN',
        page=page,
        data=data,
    )
    logger.info(f'wxsm_request__params {msg.sender} {msg.pk} {to_openid}: {params_dic}')
    resp = wx_apis.WXSubscribeMessage(**params_dic).get_result()
    logger.info(f'wxsm_request__resp {msg.sender} {msg.pk} {to_openid}: {resp}')
    is_success = resp.get('errcode') == 0 and resp.get('errmsg') == 'ok'
    msg.extra_log('wxsm', success=is_success)
    return resp


@app.task(queue=CQueueAlias.Default.value)
def send_wxsm_for_msg_one(msgid):
    """ 消息未读提醒或来电未接，微信订阅提醒 """
    from server.applibs.convert.models import Message
    from server.applibs.outside.models import CallRecord
    result = dict(
        task='send_wxsm_for_msg_one',
        msgid=msgid, reason='success',
    )
    try:
        msg = Message.objects.get(pk=msgid)
        assert msg.msg_type in [mc.MSGType.StayMsg, mc.MSGType.CallMsg]
        assert msg.reach in [mc.CallStatus.NOTCall, mc.CallStatus.ENDCalled]
        assert not msg.read_at, 'has readed'
        assert not msg.is_del, 'has del'
    except Message.DoesNotExist:
        result['reason'] = f'not exist {msgid}'
        return result
    except AssertionError as exc:
        result['reason'] = f'info wrong {msgid} {str(exc)}'
        return result
    name = filter_emoji(msg.sender_remark_name)
    page = f'/pages/child/dialog/dialog?convid={msg.convid}'
    if msg.is_call:  # 来电未接提醒
        record = CallRecord.objects.get(msgid=msg.pk)
        time_str = deal_time.time_simple(record.callers_at)
        content = f'{msg.content}，点我查看或回拨 ~'
        data = dict(name4=name, time1=time_str, thing2=content)
    else:  # 消息未读提醒
        msg_type = msg.get_msg_type_display()
        time_str = deal_time.time_simple(msg.created_at)
        data = dict(name1=name, time3=time_str, thing2=msg.content, phrase8=msg_type)
    wxsm_resp = wxsm_request(msg, page, data)
    result['wxsm_resp'] = wxsm_resp
    return result


@app.task(queue=CQueueAlias.Timed.value)
def send_wxsm_for_staymsg():
    """ 发送未读消息提醒，每三分钟执行一次 """
    from server.applibs.convert.models import Message
    now = deal_time.get_now().replace(second=0)
    assert isinstance(now, pendulum.DateTime)
    time_begin = now.add(minutes=-5)
    time_end = now.add(minutes=-2)
    msg_qs = Message.objects.filter(
        msg_type=mc.MSGType.StayMsg,
        created_at__gte=time_begin,
        created_at__lt=time_end,
        read_at__isnull=True,
        is_del=False,
    ).order_by('-pk')
    count = msg_qs.count()
    receiver_set = set()
    for msg in msg_qs:
        if msg.receiver in receiver_set:
            logger.info(f'send_wxsm_for_staymsg__repeat {msg.pk} {msg.receiver}')
            continue
        receiver_set.add(msg.receiver)
        task_wxsm = send_wxsm_for_msg_one.delay(msg.pk)
        logger.info(f'send_wxsm_for_msg_one__task {msg.pk} {task_wxsm}')
    result = dict(
        task='send_wxsm_for_staymsg',
        time_begin=time_begin.isoformat(),
        time_end=time_end.isoformat(),
        receivers=list(receiver_set),
        dealed=len(receiver_set),
        count=count,
    )
    return result


@app.task(queue=CQueueAlias.Default.value)
def send_sms_for_msg_one(msgid):
    """ 消息未读或来电未接，短信提醒 """
    from server.applibs.convert.models import Message
    result = dict(
        task='send_sms_for_msg_one',
        msgid=msgid, reason='success',
    )
    try:
        msg = Message.objects.get(pk=msgid)
        assert not msg.read_at, 'has readed'
        assert not msg.is_del, 'has del'
        is_succ, reason = msg.sms_remind()
    except Message.DoesNotExist:
        result['reason'] = f'not exist {msgid}'
        return result
    except AssertionError as exc:
        result['reason'] = f'info wrong {msgid} {str(exc)}'
        return result
    except Exception as exc:
        error_msg = f'error {msgid} {str(exc)}'
        result['reason'] = error_msg
        logger.exception(error_msg)
        return result
    result.update(is_succ=is_succ, reason=reason)
    return result


@app.task(queue=CQueueAlias.Timed.value)
def send_sms_and_wxsm_for_msg():
    """ 消息未读或来电未接，短信提醒加微信订阅提醒，每五分钟执行一次 """
    from server.applibs.convert.models import Message
    now = deal_time.get_now().replace(second=0)
    assert isinstance(now, pendulum.DateTime)
    time_begin = now.add(minutes=-15)
    time_end = now.add(minutes=-10)
    msg_qs = Message.objects.filter(
        msg_type__in=[mc.MSGType.StayMsg, mc.MSGType.CallMsg],
        reach__in=[mc.CallStatus.NOTCall, mc.CallStatus.ENDCalled],
        created_at__gte=time_begin,
        created_at__lt=time_end,
        read_at__isnull=True,
        is_del=False,
    ).order_by('-pk')
    count = msg_qs.count()
    receiver_set = set()
    for msg in msg_qs:
        if msg.receiver in receiver_set:
            logger.info(f'send_sms_and_wxsm_for_msg__repeat {msg.pk} {msg.receiver}')
            continue
        receiver_set.add(msg.receiver)
        task_sms = send_sms_for_msg_one.delay(msg.pk)
        logger.info(f'send_sms_for_msg_one__one_task {msg.pk} {task_sms}')
        task_wxsm = send_wxsm_for_msg_one.delay(msg.pk)
        logger.info(f'send_wxsm_for_msg_one__task {msg.pk} {task_wxsm}')
    result = dict(
        task='send_sms_and_wxsm_for_msg',
        time_begin=time_begin.isoformat(),
        time_end=time_end.isoformat(),
        receivers=list(receiver_set),
        dealed=len(receiver_set),
        count=count,
    )
    return result
