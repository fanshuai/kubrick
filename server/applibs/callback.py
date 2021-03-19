"""
回调
"""
import json
from django.views import View
from django.http import HttpResponse, JsonResponse
# from channels.http import AsgiRequest
from rest_framework import status

from server.djextend.drfapi import api_resp as apr
from server.djextend.drfapi.trace_req import trace_request
from server.applibs.outside.models import CallRecord
from server.applibs.billing.models import WXPay
from server.third.wechat import wx_pay


class BaseCallbackView(View):

    @staticmethod
    def get(request, *args, **kwargs):
        trace = trace_request(request)
        data = dict(_trace=trace, keys=list(request.GET.keys()))
        api_resp = apr.APIFailResp(_msg='GET方法不允许', data=data)
        resp = JsonResponse(
            data=api_resp.to_dict(),
            status=status.HTTP_405_METHOD_NOT_ALLOWED,
        )
        return resp


class YTXCallbackView(BaseCallbackView):
    """ YTX回调，话单及状态推送
    文档：https://console.ytx.net/FileDetails/FileCdrCallback
    测试：http://***.natappfree.cc/cb/ytx?**
    生产：https://api.ifand.com/cb/ytx?**
    """

    @staticmethod
    def post(request, *args, **kwargs):
        keys = list(request.GET.keys())
        data = dict(keys=keys)
        try:
            result = json.loads(request.body)
        except json.JSONDecodeError as exc:
            msg = f'JSON解析失败：{str(exc)}'
            data['_trace'] = trace_request(request)
            api_resp = apr.APIFailResp(_msg=msg, data=data)
            resp = JsonResponse(
                data=api_resp.to_dict(),
                status=status.HTTP_400_BAD_REQUEST,
            )
            return resp
        if 'Call' in keys:
            CallRecord.objects.callback_call_ytx(result['cdr'][0])
        elif 'CallState' in keys:
            CallRecord.objects.callback_status_ytx(result)
        else:
            msg = f'未识别的业务类型：{keys}'
            data['_trace'] = trace_request(request)
            api_resp = apr.APIFailResp(_msg=msg, data=data)
            resp = JsonResponse(
                data=api_resp.to_dict(),
                status=status.HTTP_400_BAD_REQUEST,
            )
            return resp
        data['_trace'] = trace_request(request)
        api_resp = apr.APIOKResp(data=data)
        resp = JsonResponse(data=api_resp.to_dict())
        return resp


class WXPayCallbackView(BaseCallbackView):
    """ 微信支付回调
    文档：https://pay.weixin.qq.com/wiki/doc/api/wxa/wxa_api.php?chapter=9_7&index=8
    配置：server/third/wechat/wx_pay.py:CBAPI_NOTIFY
    测试：http://***.natappfree.cc/cb/wxpay
    生产：https://api.ifand.com/cb/wxpay
    """

    @staticmethod
    def post(request, *args, **kwargs):
        # assert isinstance(request, AsgiRequest)
        data = wx_pay.WECHAT_PAY.parse_payment_result(request.body)
        WXPay.objects.callback_result(data)
        return HttpResponse(content=wx_pay.CB_RES)
