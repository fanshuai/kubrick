import datetime
from rest_framework import status, generics
from rest_framework.response import Response

from server.djextend.drfapi import api_resp as apr
from server.applibs.billing.models import BillDetail, BillMonth, WXPay
from .schema import validator, serializer


class ChargeWXPayApiView(generics.GenericAPIView):
    """ 微信支付充值 """

    serializer_class = validator.ChargeWXPaySerializer

    def post(self, request, *args, **kwargs):
        context = {'user': request.user}
        pay_serializer = self.serializer_class(
            data=request.data, context=context,
        )
        pay_serializer.is_valid(raise_exception=True)
        inst = pay_serializer.save()
        assert isinstance(inst, WXPay)
        data = dict(params=inst.jsapi_params, tradeno=inst.trade_no)
        return Response(data=data)


class CallBillWXPayApiView(ChargeWXPayApiView):
    """ 通话账单微信支付 """

    serializer_class = validator.CallBillWXPaySerializer


class WXPayQueryApiView(generics.GenericAPIView):
    """ 微信支付查询结果 """

    serializer_class = validator.WXPayQuerySerializer

    def post(self, request, *args, **kwargs):
        context = {'user': request.user}
        query_serializer = self.serializer_class(
            data=request.data, context=context,
        )
        query_serializer.is_valid(raise_exception=True)
        wxpay = query_serializer.validated_data['tradeno']
        success = isinstance(wxpay, WXPay) and wxpay.is_done
        data = dict(success=success, status=wxpay.status)
        return Response(data=data)


class BillMonthDetailApiView(generics.GenericAPIView):
    """ 月度账单明细 """

    serializer_class = serializer.BillMonthSerializer

    def get(self, request, *args, **kwargs):
        usrid = request.user.pk
        try:
            year, month = kwargs['year'], kwargs['month']
            month_dt = datetime.date(year, month, 1)
            month_str = month_dt.isoformat()[:7]
        except (KeyError, ValueError):
            errors = ['月份输入有误']
            drf_status = status.HTTP_400_BAD_REQUEST
            api_resp = apr.APIFailResp(data=dict(errors=errors))
            return Response(data=api_resp.to_dict(), status=drf_status)
        try:
            inst = BillMonth.objects.get(month=month_dt, usrid=usrid)
        except BillMonth.DoesNotExist:
            reason = [f'{month_str} 无记录']
            data = dict(details=[], fmt=month_str, reason=reason, count=0, amount=0)
        else:
            data = self.serializer_class(inst).data
        api_resp = apr.APIOKResp(data=data)
        return Response(data=api_resp.to_dict())


class BillUnpaidApiView(generics.GenericAPIView):
    """ 未支付账单明细 """

    serializer_class = serializer.BillDetailSerializer

    def get(self, request, *args, **kwargs):
        usrid = request.user.pk
        qs = BillDetail.objects.get_bill_unpaid_qs(usrid)
        data = self.serializer_class(qs, many=True).data
        return Response(data=dict(details=data))
