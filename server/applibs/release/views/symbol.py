"""
场景码
"""
import logging
from django.http import Http404
from rest_framework import generics
from rest_framework.response import Response
from rest_framework.exceptions import MethodNotAllowed

from server.applibs.release.models import Symbol, Vehicle, VehicleLicense
from server.djextend.drfapi import api_resp as apr
from ..schema import serializer, validator
from ...account.models import Phone

logger = logging.getLogger('kubrick.debug')


class SymbolsApiView(generics.GenericAPIView):
    """ 场景码列表 """
    serializer_class = serializer.SymbolSerializer

    def get(self, request, *args, **kwargs):
        symbol_qs = Symbol.objects.user_symbol_qs(request.user.pk)
        symbols = self.serializer_class(symbol_qs, many=True).data
        data = dict(symbols=symbols)
        return Response(data=data)


class SymbolViewApiView(generics.GenericAPIView):
    """ 场景码详情 """
    serializer_class = serializer.SymbolViewSerializer

    def get_symbol(self, kwargs):
        try:
            symbol_qs = Symbol.objects.user_symbol_qs(self.request.user.pk)
            symbol = symbol_qs.get(symbol=kwargs['symbol'])
            assert symbol.is_usable
        except (Symbol.DoesNotExist, KeyError, AssertionError):
            raise Http404
        return symbol

    def get(self, request, *args, **kwargs):
        symbol = self.get_symbol(kwargs)
        data = self.serializer_class(symbol).data
        return Response(data=data)


class SymbolStatusApiView(SymbolViewApiView):
    """ 场景码用户状态 """

    serializer_class = serializer.SymbolViewSerializer

    def get(self, request, *args, **kwargs):
        raise MethodNotAllowed

    def post(self, request, *args, **kwargs):
        symbol = self.get_symbol(kwargs)
        is_open = kwargs['status'] == 'open'
        symbol.user_status(is_open)
        data = self.serializer_class(symbol).data
        return Response(data=data)


class SymbolTitleApiView(SymbolViewApiView):
    """ 场景码 别名修改 """

    serializer_class = validator.SymbolTitleSerializer

    def get(self, request, *args, **kwargs):
        raise MethodNotAllowed

    def post(self, request, *args, **kwargs):
        symbol = self.get_symbol(kwargs)
        st_serializer = self.serializer_class(
            data=request.data,
            context={'user': request.user, 'symbol': symbol},
        )
        st_serializer.is_valid(raise_exception=True)
        title = st_serializer.validated_data['title']
        symbol.set_title(title)
        data = serializer.SymbolViewSerializer(symbol).data
        return Response(data=data)


class SymbolSelfdomApiView(SymbolViewApiView):
    """ 场景码 自定义签名 """

    serializer_class = validator.SymbolSelfdomSerializer

    def get(self, request, *args, **kwargs):
        raise MethodNotAllowed

    def post(self, request, *args, **kwargs):
        sd_serializer = self.serializer_class(
            data=request.data,
            context={'user': request.user},
        )
        sd_serializer.is_valid(raise_exception=True)
        symbol = self.get_symbol(kwargs)
        selfdom = sd_serializer.validated_data['selfdom']
        symbol.set_selfdom(selfdom)
        data = serializer.SymbolViewSerializer(symbol).data
        return Response(data=data)


class SymbolLeaveApiView(SymbolViewApiView):
    """ 解除绑定，发送验证码 """

    def post(self, request, *args, **kwargs):
        symbol = self.get_symbol(kwargs)
        phone = Phone.objects.user_phone_main(request.user.pk)
        if not phone:
            api_resp = apr.APIFailResp(_msg='暂未绑定手机号', data=dict(symbol=symbol.symbol))
            return Response(data=api_resp.to_dict())
        is_send, resp = phone.captcha_send_for_symbol_strike()
        logger.info(f'captcha_send_for_symbol_strike__done {symbol.symbol} {phone.summary} {is_send} {resp}')
        data = dict(phone=phone.show, symbol=symbol.symbol)
        if is_send:
            api_resp = apr.APIOKResp(data=data)
        else:
            api_resp = apr.APIFailResp(_msg=resp, data=data)
        return Response(data=api_resp.to_dict())


class SymbolUnbindApiView(SymbolLeaveApiView):
    """ 解除绑定，验证验证码 """
    serializer_class = validator.SymbolUnbindSerializer

    def post(self, request, *args, **kwargs):
        symbol = self.get_symbol(kwargs)
        su_serializer = self.serializer_class(
            data=request.data,
            context={'user': request.user, 'symbol': symbol},
        )
        su_serializer.is_valid(raise_exception=True)
        symbol.status_delete()
        count = Symbol.objects.user_symbol_qs(request.user.pk).count()
        data = dict(count=count)
        return Response(data=data)


class VehicleBindApiView(generics.GenericAPIView):
    """ 行驶证认证，车辆绑定 """

    serializer_class = validator.VehicleLicenseImgSerializer

    def post(self, request, *args, **kwargs):
        img_serializer = self.serializer_class(
            data=request.data,
            context={'user': request.user},
        )
        img_serializer.is_valid(raise_exception=True)
        oss_key = img_serializer.validated_data['img']
        inst = VehicleLicense.objects.vehicle_license_add(oss_key, request.user.pk)
        if inst.is_verified:
            is_ok, resp = Vehicle.objects.bind_vehicle_symbol(inst)
        else:
            is_ok, resp = False, inst.reason
        if is_ok:
            assert isinstance(resp, Symbol)
            data = serializer.SymbolSerializer(resp).data
            api_resp = apr.APIOKResp(data=data)
        else:
            api_resp = apr.APIFailResp(_msg=resp, data={})
        return Response(data=api_resp.to_dict())
