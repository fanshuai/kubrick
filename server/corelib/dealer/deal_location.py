"""
位置坐标处理
"""
import json
import logging
from sentry_sdk import capture_message

logger = logging.getLogger('kubrick.debug')


def get_location_value(value):
    if not isinstance(value, dict):
        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            val_type, exc_type = type(exc), type(exc).__name__
            logger.warning(f'get_location_value__decode_error {val_type} {exc_type} {value}')
            capture_message('get_location_value__decode_error')
            return None
    # 至少包含：纬度、经度
    keys = ('latitude', 'longitude')
    for key in keys:
        val = value.get(key)
        if not isinstance(val, (int, float)):
            return None
    return value


def get_location_point(location):
    """ 获取位置坐标信息，latitude、longitude：纬度、经度 """
    point_none = None
    if not isinstance(location, dict):
        return point_none
    for key in ('latitude', 'longitude'):
        val = location.get(key)
        if not isinstance(val, (int, float)):
            return point_none
    point = (
        location['latitude'],
        location['longitude'],
    )
    return point
