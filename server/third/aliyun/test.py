"""
https://help.aliyun.com/document_detail/72746.html

点击拨号：
    https://help.aliyun.com/document_detail/61101.html
    https://help.aliyun.com/document_detail/114040.html

呼入动态IVR，呼转回调http接口规范：
    https://help.aliyun.com/document_detail/98176.html
    https://help.aliyun.com/document_detail/112702.html

取消呼叫：
    https://help.aliyun.com/document_detail/62338.html
    https://help.aliyun.com/document_detail/114039.html

消息回执：
    https://help.aliyun.com/document_detail/112503.html

查询指定通话的呼叫详情：
    https://help.aliyun.com/document_detail/114046.html
"""
from aliyunsdkcore.request import CommonRequest

from server.third.aliyun import client

request = CommonRequest()
request.set_accept_format('json')
request.set_domain('dyvmsapi.aliyuncs.com')
request.set_method('POST')
request.set_protocol_type('https')
request.set_version('2017-05-25')
request.set_action_name('ClickToDial')

request.add_query_param('CallerShowNumber', "18610559223")
request.add_query_param('CallerNumber', "18610559223")
request.add_query_param('CalledShowNumber', "18610559223")
request.add_query_param('CalledNumber', "18610559223")

response = client.do_action_with_exception(request)
print(str(response, encoding='utf-8'))
