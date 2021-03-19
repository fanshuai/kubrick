"""
DRF常量、枚举值
"""
import json
from inspect import getmembers
from rest_framework import status
from corsheaders.defaults import default_headers


# ###################### 异常消息定义
API_EXCEPTION = 'Whoops, something went wrong on our end.'


# ###################### HTTP 状态码定义
API_STATUS = {v: k.replace(f'HTTP_{v}_', '') for k, v in getmembers(status) if isinstance(v, int)}


def get_code_status(code=status.HTTP_200_OK):
    return API_STATUS.get(code, '-')


# ###################### HTTP 请求头定义
HD_APPID = 'x-appid'
HD_TOKEN = 'x-token'
HD_TIMESTAMP = 'x-timestamp'
HD_SIGNATURE = 'x-signature'


def header_to_meta_key(key):
    key = str(key).upper()
    meta_key = f"HTTP_{key.replace('-', '_')}"
    return meta_key


EXPAND_CORS_HEADERS = (HD_APPID, HD_TOKEN, HD_TIMESTAMP, HD_SIGNATURE)
ALLOW_CORS_HEADERS = list(default_headers) + list(EXPAND_CORS_HEADERS)


if __name__ == '__main__':
    print(json.dumps(API_STATUS, indent=2))
