"""
时间处理
"""
import datetime
import pendulum
from sentry_sdk import capture_exception
from pendulum.exceptions import ParserError

from server.constant.normal import TZCN, LGZH


def utc_now():
    """ 当前UTC时间、去毫秒 """
    now = pendulum.now(tz='UTC').replace(microsecond=0)
    assert isinstance(now, pendulum.DateTime)
    return now


def get_now():
    """ 当前时区时间、去毫秒 """
    now = pendulum.now(tz=TZCN).replace(microsecond=0)
    assert isinstance(now, pendulum.DateTime)
    return now


def get_now_str():
    """ 当前时间字符串、去毫秒，东八区 """
    now_str = get_now().isoformat()
    return now_str


def time_tzcn(dt):
    """ 时间时区转换 """
    new_dt = pendulum.instance(dt).in_tz(TZCN)
    return new_dt


def time_floor_ts(dt):
    """ 时间保留到秒，去毫秒 """
    new_dt = time_tzcn(dt).replace(microsecond=0)
    return new_dt


def time_floor_day(dt):
    """ 时间保留到天，去时分秒 """
    new_dt = time_tzcn(dt).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0
    )
    return new_dt


def time_simple(dt):
    """ 时间格式化，保留到分钟 """
    simple_str = pendulum.instance(dt).in_tz(TZCN).format('YYYY-MM-DD HH:mm')
    return simple_str


def diff_humans(dt):
    """ 过去多长时间，eg: 5分钟前 """
    new_dt = time_floor_ts(dt)
    assert isinstance(new_dt, pendulum.DateTime)
    desc = new_dt.diff_for_humans(locale=LGZH)
    return desc


def show_humanize(dt):
    """ 易读时间 """
    dt = time_floor_ts(dt)
    assert isinstance(dt, pendulum.DateTime)
    diff = get_now().diff(dt)
    time_fmt = dt.format('HH:mm')
    diff_days = diff.in_days()
    if diff_days < 1:
        desc = f'今天 {time_fmt}'
    elif diff_days == 1:
        desc = f'昨天 {time_fmt}'
    elif 1 < diff_days < 5:
        week_fmt = dt.format('dddd', locale=LGZH)
        desc = f'{week_fmt} {time_fmt}'
    elif diff.in_years() == 0:
        date_fmt = dt.format('MM-DD')
        desc = f'{date_fmt} {time_fmt}'
    else:
        year_fmt = dt.format('YYYY-MM-DD')
        desc = f'{year_fmt} {time_fmt}'
    return desc


def show_humanize_simple(dt):
    """ 易读时间简版，会话列表使用 """
    dt = time_floor_ts(dt)
    assert isinstance(dt, pendulum.DateTime)
    diff = get_now().diff(dt)
    diff_days = diff.in_days()
    if diff_days < 1:
        desc = dt.format('HH:mm')
    elif diff_days == 1:
        desc = '昨天'
    elif 1 < diff_days < 7:
        desc = dt.format('dddd', locale=LGZH)
    elif diff.in_years() == 0:
        desc = dt.format('M月D日')
    else:
        desc = dt.format('Y年M月')
    return desc


def get_aware_now(now=None):
    """ 时间添加时区 """
    if isinstance(now, datetime.datetime):
        if now.utcoffset() is None:
            now = pendulum.instance(now, tz=TZCN)
        else:
            now = pendulum.instance(now).in_tz(TZCN)
    else:
        now = pendulum.now(tz=TZCN)
    return now


def get_tzcn_format(dt):
    """ 时间格式化，Asia/Shanghai """
    if isinstance(dt, datetime.datetime):
        if dt.utcoffset() is None:
            dt = pendulum.instance(dt, tz=TZCN)
        else:
            dt = pendulum.instance(dt).in_tz(TZCN)
        dt_str = dt.format('YYYY-MM-DD HH:mm:ss')
    else:
        dt_str = ''
    return dt_str


def get_tzcn_parse(dt_str):
    """ 解析格式化时间，Asia/Shanghai """
    if not dt_str:
        return None
    try:
        dt = pendulum.parse(dt_str, tz=TZCN)
        assert isinstance(dt, pendulum.DateTime)
        dt = dt.in_tz(TZCN)
    except (ParserError, AssertionError) as exc:
        capture_exception(exc)
        dt = None
    return dt


def get_tzcn_date_parse(dt_str):
    """ 解析格式化日期，Asia/Shanghai """
    dt = get_tzcn_parse(dt_str)
    if isinstance(dt, pendulum.DateTime):
        return dt.date()
    return None


def round_floor_ten_mins(now=None):
    """
    获取时间区间，以10分钟向下取整并分隔
    10:32 > 10:10 ~ 10:20
    """
    now = get_aware_now(now)
    now = now.replace(second=0, microsecond=0)
    assert isinstance(now, pendulum.DateTime)
    now = now.add(minutes=-5)  # 时间提前，冗余5分钟
    minute_end = (now.minute // 10) * 10
    time_end = now.replace(minute=minute_end)
    assert isinstance(time_end, pendulum.DateTime)
    time_start = time_end.add(minutes=-10)
    return time_start, time_end


def every_five_hours(now=None):
    """ 过去5小时时间区间 """
    now = get_aware_now(now)
    time_end = now.replace(minute=0, second=0, microsecond=0)
    assert isinstance(time_end, pendulum.DateTime)
    time_begin = time_end.add(hours=-5)
    return time_begin, time_end


if __name__ == '__main__':
    no = pendulum.now(tz=TZCN)
    for i in range(100):
        n = no.add(minutes=i)
        print(i, n.isoformat(), round_floor_ten_mins(n))
    print(round_floor_ten_mins())
