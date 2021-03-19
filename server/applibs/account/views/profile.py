"""
个人信息
"""
import logging
from rest_framework import generics
from rest_framework import throttling
from rest_framework.views import APIView
from rest_framework.response import Response
from silk.profiling.profiler import silk_profile
from rest_framework.exceptions import MethodNotAllowed

from server.applibs.outside.models import ImageOcr
from server.applibs.account.models import AuthUser, UserCode, UserDevice
from server.djextend.drfapi.drf_throttle import ScopedThrottles
from server.djextend.drfapi import api_resp as apr
from ..schema import validator, serializer
from ..tasks import update_usercode_qrimg

logger = logging.getLogger('kubrick.debug')


class ProfileApiView(generics.GenericAPIView):
    """ 个人信息修改 """
    throttle_classes = (throttling.ScopedRateThrottle,)
    throttle_scope = ScopedThrottles.Profile.name.lower()
    serializer_class = validator.ProfileSerializer

    def get(self, request, *args, **kwargs):
        user_dic = serializer.UserSelfSerializer(instance=self.request.user).data
        return Response(data=dict(user=user_dic))

    def post(self, request, *args, **kwargs):
        profile_serializer = self.serializer_class(
            data=request.data,
            context={'user': request.user},
        )
        profile_serializer.is_valid(raise_exception=True)
        update_usercode_qrimg.delay(request.user.pk)
        return self.get(request, *args, **kwargs)


class ProfileBioApiView(generics.GenericAPIView):
    """ 用户 个性签名 """

    serializer_class = validator.ProfileBioSerializer

    def get(self, request, *args, **kwargs):
        raise MethodNotAllowed

    def post(self, request, *args, **kwargs):
        pb_serializer = self.serializer_class(
            data=request.data,
            context={'user': request.user},
        )
        pb_serializer.is_valid(raise_exception=True)
        user_dic = serializer.UserSelfSerializer(instance=request.user).data
        return Response(data=dict(user=user_dic))


class UserCodeApiView(generics.GenericAPIView):
    """ 用户码 """
    serializer_class = serializer.UserSelfSerializer

    @property
    def qrcode_info_dic(self):
        user = self.request.user
        assert isinstance(user, AuthUser)
        uc_info = user.usercode_info
        data = dict(
            qrurl=uc_info.qr_uri,
            qrimg=uc_info.qrimg_url,
            version=uc_info.version,
        )
        return data

    def get(self, request, *args, **kwargs):
        user_dic = self.serializer_class(instance=request.user).data
        data = dict(user=user_dic, **self.qrcode_info_dic)
        return Response(data=data)

    @silk_profile(name='用户码重置')
    def post(self, request, *args, **kwargs):
        """ 用户二维码重置 """
        uc_info = request.user.usercode_info
        assert isinstance(uc_info, UserCode)
        is_ok, msg = uc_info.qrcode_reset()
        msg = '已重置' if is_ok else msg
        user_dic = self.serializer_class(instance=request.user).data
        data = dict(user=user_dic, **self.qrcode_info_dic)
        if is_ok:
            api_resp = apr.APIOKResp(_msg=msg, data=data)
        else:
            api_resp = apr.APIFailResp(_msg=msg, data=data)
        return Response(data=api_resp.to_dict())


class IDCardImgApiView(generics.GenericAPIView):
    """ 用户身份证实名认证 """
    serializer_class = validator.IDCardImgSerializer

    def post(self, request, *args, **kwargs):
        imgs_serializer = self.serializer_class(
            data=request.data,
            context={'user': request.user},
        )
        imgs_serializer.is_valid(raise_exception=True)
        img_front, img_back = imgs_serializer.validated_data['imgs']
        is_ok, resp = ImageOcr.objects.idcard_image_ocr(img_front, img_back, request.user.pk)
        user_dic = serializer.UserSelfSerializer(instance=request.user).data
        data = dict(user=user_dic)
        if is_ok:
            api_resp = apr.APIOKResp(data=data)
        else:
            api_resp = apr.APIFailResp(_msg=resp, data=data)
        return Response(data=api_resp.to_dict())


class DeviceListApiView(APIView):
    """ 用户登录设备列表 """

    def get(self, request, *args, **kwargs):
        usrid = request.user.pk
        key = self.request.session.session_key
        devices = UserDevice.objects.user_device_list(usrid, key=key)
        return Response(data=dict(devices=devices))


class DeviceLogoutApiView(generics.GenericAPIView):
    """ 设备管理，注销登录 """
    serializer_class = validator.DeviceLogoutSerializer

    def post(self, request, *args, **kwargs):
        usrid = request.user.pk
        key = request.session.session_key
        logout_serializer = self.serializer_class(
            data=request.data,
            context={'request': request},
        )
        logout_serializer.is_valid(raise_exception=True)
        devices = UserDevice.objects.user_device_list(usrid, key=key)
        return Response(data=dict(devices=devices))
