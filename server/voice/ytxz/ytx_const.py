from enum import unique
from django.db.models import TextChoices

from kubrick.initialize import IS_PROD_ENV


# if IS_PROD_ENV:
#     REST_URL = 'http://api.ytx.net'
#     YTX_APPID = '39d33028efb24725a198fb08b67f2a77'
# else:  # YTX沙箱环境
#     YTX_APPID = 'ff1f324a0604417c9c7f5f1186225fda'
#     REST_URL = 'http://sandbox.ytx.net'


REST_URL = 'http://api.ytx.net'

if IS_PROD_ENV:  # YTX应用名称：DAOWO
    YTX_APPID = '39d33028efb24725a198fb08b67f2a77'
else:  # YTX应用名称：DAOWO-DEV
    YTX_APPID = '614716309d884107960eb5c7cfe454e0'


ACCOUNT_SID = 'ee76c8fe84364a5f8623bc4528debe30'
AUTH_TOKEN = 'a3d31d347f8b401a9a1baf263abab8ae'


YTX_ERROR_CODES = (
    (0, '提交成功'),
    (-1, '号码无效'),
    (-2, '缺少必要参数'),
    (-3, '无效action'),
    (-4, '无效的JSON'),
    (-100, '异常错误'),
    (-101, '参数不合法'),
    (-102, '电话号码不合法'),
    (-200, '无此用户'),
    (-201, '用户状态失效'),
    (-202, '包头验证信息错误'),
    (-203, 'AuthToken验证失败'),
    (-204, '账户余额不足'),
    (-205, '应用验证失败'),
)


@unique
class YTXCallState(TextChoices):
    """ YTX双向呼叫，状态推送 """
    Callout = 'callout', '呼出'
    Alerting = 'alerting', '振铃'
    Answer = 'answer', '接听'
    Disconnect = 'disconnect', '结束'


# 外显号
YTX_SHOW_NUM = '057128234805'
YTX_SHOW_NUM_FMT = '(0571) 2823 4805'
