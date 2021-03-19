"""
手机号
"""
import logging
from rest_framework import generics
from rest_framework.response import Response

from server.djextend.drfapi import api_resp as apr
from ..logic.get_phones import get_user_phones
from ..schema import validator, serializer

logger = logging.getLogger('kubrick.debug')


class PhonesApiView(generics.GenericAPIView):
    """ 手机号列表 """
    serializer_class = serializer.PhoneSerializer

    def get(self, request, *args, **kwargs):
        usrid = self.request.user.pk
        data = get_user_phones(usrid)
        return Response(data=data)


class PhoneAddApiView(generics.GenericAPIView):
    """ 绑定，发送验证码 """
    serializer_class = validator.PhoneAddSerializer

    def post(self, request, *args, **kwargs):
        add_serializer = self.serializer_class(
            data=request.data,
            context={'user': request.user},
        )
        add_serializer.is_valid(raise_exception=True)
        data = add_serializer.validated_data
        phone = data['phone']
        is_send, resp = phone.captcha_send_for_bind()
        logger.info(f'captcha_send_for_bind__done {phone.summary} {is_send} {resp}')
        request.session['bind_pnvid'] = resp
        request.session['bind_phoneid'] = phone.pk
        request.session['bind_usrid'] = phone.usrid
        data = dict(phone=phone.show)
        if is_send:
            api_resp = apr.APIOKResp(data=data)
        else:
            api_resp = apr.APIFailResp(_msg=resp, data=data)
        return Response(data=api_resp.to_dict())


class PhoneBindApiView(generics.GenericAPIView):
    """ 绑定，验证验证码 """
    serializer_class = validator.PhoneBindSerializer

    def post(self, request, *args, **kwargs):
        usrid = self.request.user.pk
        bind_serializer = self.serializer_class(
            data=request.data,
            context={'user': request.user},
        )
        bind_serializer.is_valid(raise_exception=True)
        data = get_user_phones(usrid)
        return Response(data=data)


class WXPhoneBindApiView(PhoneBindApiView):
    """ 绑定，微信手机号解密 """
    serializer_class = validator.WXPhoneBindSerializer


class PhoneMainApiView(generics.GenericAPIView):
    """ 设定为主手机号 """
    serializer_class = validator.PhoneMainSerializer

    def post(self, request, *args, **kwargs):
        usrid = self.request.user.pk
        main_serializer = self.serializer_class(
            data=request.data,
            context={'user': request.user},
        )
        main_serializer.is_valid(raise_exception=True)
        user_dic = serializer.UserSelfSerializer(instance=request.user).data
        data = get_user_phones(usrid)
        data['user'] = user_dic
        return Response(data=data)


class PhoneLeaveApiView(generics.GenericAPIView):
    """ 解除绑定，发送验证码 """
    serializer_class = validator.PhoneLeaveSerializer

    def post(self, request, *args, **kwargs):
        pl_serializer = self.serializer_class(
            data=request.data,
            context={'user': request.user},
        )
        pl_serializer.is_valid(raise_exception=True)
        phone = pl_serializer.validated_data['key']
        is_send, pnvid = phone.captcha_send_for_unbind()
        logger.info(f'captcha_send_for_unbind__done {phone.summary} {is_send} {pnvid}')
        data = dict(phone=phone.show)
        return Response(data=data)


class PhoneUnbindApiView(PhoneMainApiView):
    """ 解除绑定，验证验证码 """
    serializer_class = validator.PhoneUnbindSerializer
