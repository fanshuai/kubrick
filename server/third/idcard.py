"""
身份证实名认证

https://market.aliyun.com/products/57000002/cmapi022049.html

使用额度查看：https://market.console.aliyun.com/imageconsole/index.htm
https://market.console.aliyun.com/imageconsole/index.htm#/api/cmapi022049

{
    "status":"01",
    "msg":"实名认证通过！",
    "idCard":"4***9",
    "name":"**",
    "sex":"*",
    "area":"***",
    "province":"**",
    "city":"**",
    "prefecture":"**",
    "birthday":"****",
    "addrCode":"**",
    "lastCode":"9"
}
"""
import logging
import requests

logger = logging.getLogger('kubrick.api')

appcode = '7da04ca7f9b24af4a367c7ddde4f4943'
api_host = 'https://idcert.market.alicloudapi.com/idcard'


def alicloudapi_idcard_verify(name, idcard):
    """ 身份证实名认证 """
    params = dict(idCard=idcard, name=name)
    headers = dict(Authorization=f'APPCODE {appcode}')
    resp = requests.get(api_host, params=params, headers=headers)
    if resp.status_code == 200:
        resp_dic = resp.json()
        is_ok = resp_dic['status'] == '01'  # 状态码:详见状态码说明 01 通过，02不通过
        msg = resp_dic['msg']
        if is_ok:
            return True, msg
        logger.warning(f'idcard_verify__fail {name}: {resp_dic}')
        return False, msg
    logger.warning(f'idcard_verify__error {resp.status_code} {resp.content}')
    return False, '认证服务暂不可用，请稍后重试'
