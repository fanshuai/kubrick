"""
ClickToDial
语音双呼，点击呼叫（点击拨号）
https://help.aliyun.com/document_detail/114040.html
https://help.aliyun.com/document_detail/147561.html
https://help.aliyun.com/document_detail/114046.html
https://help.aliyun.com/document_detail/147566.html
"""
from aliyunsdkdyvmsapi.request.v20170525.CancelCallRequest import CancelCallRequest
from aliyunsdkdyvmsapi.request.v20170525.ClickToDialRequest import ClickToDialRequest
from aliyunsdkdyvmsapi.request.v20170525.QueryCallDetailByCallIdRequest import QueryCallDetailByCallIdRequest

from server.third.aliyun import AliReqAction


def click_to_dial():
    """ 点击呼叫 """
    request = ClickToDialRequest()
    request.set_accept_format('json')
    request.set_CallerShowNumber('123xxxx')
    request.set_CallerNumber('1575xxxx')
    request.set_CalledShowNumber('12xxxx')
    request.set_CalledNumber('1885xxxx')
    resp_dic = AliReqAction(request).do_req_action()
    print(resp_dic)
    return resp_dic


def query_call_detail():
    """ 查询通话记录详情 """
    request = QueryCallDetailByCallIdRequest()
    request.set_accept_format('json')
    request.set_CallId('100625930001^10019107xx')
    request.set_ProdId(11000000300004)  # 语音双呼
    request.set_QueryDate(1577255564)
    resp_dic = AliReqAction(request).do_req_action()
    print(resp_dic)
    return resp_dic


def cancel_call():
    """ 取消点击呼叫 """
    request = CancelCallRequest()
    request.set_accept_format('json')
    request.set_CallId('117059405036^10385912xx')
    resp_dic = AliReqAction(request).do_req_action()
    print(resp_dic)
    return resp_dic
